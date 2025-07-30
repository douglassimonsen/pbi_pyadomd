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
from pathlib import Path
from sys import path
from typing import TYPE_CHECKING, Any, NamedTuple, Self, TypeVar

import bs4
import clr  # type: ignore[import-untyped]
import structlog

from .c_sharp_type_mapping import adomd_type_map, convert
from .Microsoft.AnalysisServices.enums import ConnectionState

logger = structlog.get_logger()
T = TypeVar("T")


path.append(str(Path(__file__).parent)[2:])
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")  # pyright: ignore reportAttributeAccessIssue
from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
    AdomdCommand,
    AdomdConnection,
    AdomdErrorResponseException,
    AdomdUnknownResponseException,
)

if TYPE_CHECKING:
    from types import TracebackType

    from Microsoft.AnalysisServices.AdomdClient import IDataReader

__all__ = ["AdomdErrorResponseException"]


class Description(NamedTuple):
    name: str
    type_code: str


class Reader:
    _reader: "IDataReader"

    def __init__(self, reader: "IDataReader") -> None:
        self._reader = reader

    def read(self) -> bool:
        try:
            return self._reader.Read()
        except AdomdUnknownResponseException:
            return False

    def read_outer_xml(self) -> str:
        return self._reader.ReadOuterXml()

    def column_names(self) -> list[str]:
        """Returns the column names of the last executed query."""
        return [self._reader.GetName(i) for i in range(self.field_count)]

    def descriptions(self) -> list[Description]:
        return [
            Description(
                self._reader.GetName(i),
                adomd_type_map[self._reader.GetFieldType(i).ToString()].type_name,
            )
            for i in range(self.field_count)
        ]

    def get_row(self) -> tuple[Any, ...]:
        return tuple(
            convert(
                self._reader.GetFieldType(i).ToString(),
                self._reader[i],
                adomd_type_map,
            )
            for i in range(self.field_count)
        )

    @property
    def field_count(self) -> int:
        return self._reader.FieldCount

    @property
    def is_closed(self) -> bool:
        return self._reader.IsClosed

    def close(self) -> None:
        self._reader.Close()


class Cursor:
    reader: Reader
    _conn: AdomdConnection

    def __init__(self, connection: AdomdConnection) -> None:
        self._conn = connection
        self._description: list[Description] = []

    def close(self) -> None:
        if self.is_closed:
            return
        self.reader.close()

    def execute_xml(
        self, query: str, query_name: str | None = None,
    ) -> bs4.BeautifulSoup:
        def _is_encoded_char(val: str) -> bool:
            UTF_ENCODED_LEN = 5  # noqa: N806
            start, body = val[0], val[1:]
            return (
                len(val) == UTF_ENCODED_LEN
                and start == "x"
                and all(c in "0123456789ABCDEF" for c in body)
            )

        def _clean_name(name: str) -> str:
            name_parts = name.split("_")
            for i, e in enumerate(name_parts):
                if _is_encoded_char(e):
                    name_parts[i] = chr(int(e[1:], 16))
            return "_".join(name_parts)

        query_name = query_name or ""
        logger.debug("execute XML query", query_name=query_name)
        self._cmd = AdomdCommand(query, self._conn)
        self.reader = Reader(self._cmd.ExecuteXmlReader())
        logger.debug("reading query", query_name=query_name)
        lines = [self.reader.read_outer_xml()]
        while lines[-1] != "":
            lines.append(self.reader.read_outer_xml())
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
        self.reader = Reader(self._cmd.ExecuteReader())

        logger.debug("reading query", query_name=query_name)

        return self

    def column_names(self) -> list[str]:
        """Returns the column names of the last executed query."""
        return self.reader.column_names()

    def fetch_stream(self) -> Iterator[dict[str, Any]]:
        """Fetches the rows from the last executed query as a stream of dictionaries.

        Note:
        ----
            This is important for subscribe queries that return a stream of data.

        """
        column_names = self.column_names()
        while self.reader.read():
            yield dict(zip(column_names, self.fetch_one_tuple(), strict=False))

    def fetch_one_tuple(self) -> tuple[Any, ...]:
        """Fetches a single row from the last executed query as a tuple.

        Note:
            Used internally for performance.

        """
        return self.reader.get_row()

    def fetch_one(self) -> dict[str, Any]:
        """Fetches a single row from the last executed query as a dictionary.

        Returns:
            dict[str, Any]: A dictionary representing the row, with column names as keys

        """
        column_names = self.column_names()
        data = self.reader.get_row()
        return dict(zip(column_names, data, strict=False))

    def fetch_many(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetches multiple rows from the last executed query.

        Args:
            limit (int | None): The number of rows to fetch. If None, fetches all rows.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing the rows.

        """
        # mypy issues with list comprehension :-(
        if limit is not None:
            return [self.fetch_one() for _ in range(limit) if self.reader.read()]
        return list(self.fetch_stream())

    @property
    def is_closed(self) -> bool:
        try:
            state: bool = self.reader.is_closed
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
    def state(self) -> ConnectionState:
        """1 = Open, 0 = Closed."""
        return ConnectionState(self.conn.State.value__)

    def __enter__(self) -> Self:
        if self.state != ConnectionState.Open:
            self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: "TracebackType | None",  # noqa: PYI036
    ) -> None:
        self.close()
