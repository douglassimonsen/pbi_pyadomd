"""Copyright 2020 SCOUT.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

# mypy: ignore-errors
from collections.abc import Iterator
from enum import IntEnum
from pathlib import Path
from sys import path
from typing import TYPE_CHECKING, Any, NamedTuple, Self, TypeVar

import bs4
import clr  # type: ignore[import-untyped]
import structlog

from .c_sharp_type_mapping import adomd_type_map, convert

logger = structlog.get_logger()
T = TypeVar("T")


path.append(str(Path(__file__).parent)[2:])
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")  # pyright: ignore reportAttributeAccessIssue
from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
    AdomdCommand,
    AdomdConnection,
    AdomdErrorResponseException,
)

if TYPE_CHECKING:
    from types import TracebackType

    from Microsoft.AnalysisServices.AdomdClient import IDataReader

__all__ = ["AdomdErrorResponseException"]


class Description(NamedTuple):
    name: str
    type_code: str


class Cursor:
    _reader: "IDataReader"
    _conn: AdomdConnection

    def __init__(self, connection: AdomdConnection) -> None:
        self._conn = connection
        self._description: list[Description] = []

    def close(self) -> None:
        if self.is_closed:
            return
        self._reader.Close()

    def execute_xml(
        self, query: str, query_name: str | None = None
    ) -> bs4.BeautifulSoup:
        def _is_encoded_char(val: str) -> bool:
            UTF_ENCODED_LEN = 5  # noqa: N806
            start, body = val[0], val[1:]
            if (
                len(val) == UTF_ENCODED_LEN
                and start == "x"
                and all(c in "0123456789ABCDEF" for c in body)
            ):
                return True
            return False

        def _clean_name(name: str) -> str:
            name_parts = name.split("_")
            for i, e in enumerate(name_parts):
                if _is_encoded_char(e):
                    name_parts[i] = chr(int(e[1:], 16))
            return "_".join(name_parts)

        query_name = query_name or ""
        logger.debug("execute XML query", query_name=query_name)
        self._cmd = AdomdCommand(query, self._conn)
        self._reader = self._cmd.ExecuteXmlReader()
        logger.debug("reading query", query_name=query_name)
        lines = [self._reader.ReadOuterXml()]
        while lines[-1] != "":  # noqa: PLC1901
            lines.append(self._reader.ReadOuterXml())
        ret = bs4.BeautifulSoup("".join(lines), "xml")
        for node in ret.find_all():
            assert isinstance(node, bs4.element.Tag)
            node.name = _clean_name(node.name)
        return ret

    def execute_non_query(self, query: str, query_name: str | None = None) -> Self:
        query_name = query_name or ""
        logger.debug("execute DAX query", query_name=query_name)
        self._cmd = AdomdCommand(query, self._conn)
        self._cmd.ExecuteNonQuery()
        return self

    def execute_dax(self, query: str, query_name: str | None = None) -> Self:
        query_name = query_name or ""
        logger.debug("execute DAX query", query_name=query_name)
        self._cmd = AdomdCommand(query, self._conn)
        self._reader = self._cmd.ExecuteReader()
        self._field_count = self._reader.FieldCount

        logger.debug("reading query", query_name=query_name)
        for i in range(self._field_count):
            self._description.append(
                Description(
                    self._reader.GetName(i),
                    adomd_type_map[self._reader.GetFieldType(i).ToString()].type_name,
                ),
            )
        return self

    def fetch_stream(self) -> Iterator[tuple[Any, ...]]:
        while self._reader.Read():
            yield self.fetchone()

    def fetch_stream_dict(self) -> Iterator[dict[str, Any]]:
        column_names = [self._reader.GetName(i) for i in range(self._field_count)]
        while self._reader.Read():
            yield dict(zip(column_names, self.fetchone()))

    def fetchone(self) -> tuple[Any, ...]:
        return tuple(
            convert(
                self._reader.GetFieldType(i).ToString(),
                self._reader[i],
                adomd_type_map,
            )
            for i in range(self._field_count)
        )

    def fetchmany(self, size: int = 1) -> list[tuple[Any, ...]]:
        ret: list[tuple[Any, ...]] = []
        try:
            for _ in range(size):
                ret.append(self.fetchone())
        except StopIteration:
            pass
        return ret

    def fetchall(self) -> list[tuple[Any, ...]]:
        """Fetches all the rows from the last executed query."""
        # mypy issues with list comprehension :-(
        return list(self.fetch_stream())

    @property
    def is_closed(self) -> bool:
        try:
            state: bool = self._reader.IsClosed
        except AttributeError:
            return True
        return state

    @property
    def description(self) -> list[Description]:
        return self._description

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: "TracebackType | None",  # noqa: PYI036
    ) -> None:
        self.close()


class AdmomdState(IntEnum):
    OPEN = 1
    CLOSED = 0


class Pyadomd:
    def __init__(self, conn_str: str) -> None:
        self.conn = AdomdConnection(conn_str)

    def clone(self) -> "Pyadomd":
        """Clones the connection."""
        return Pyadomd(self.conn.ConnectionString)

    def close(self) -> None:
        """Closes the connection."""
        self.conn.Close()
        self.conn.Dispose()

    def open(self) -> Self:
        """Opens the connection."""
        self.conn.Open()
        return self

    def cursor(self) -> Cursor:
        """Creates a cursor object."""
        return Cursor(self.conn)

    @property
    def state(self) -> AdmomdState:
        """1 = Open, 0 = Closed."""
        return AdmomdState(self.conn.State)

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: "TracebackType | None",  # noqa: PYI036
    ) -> None:
        self.close()
