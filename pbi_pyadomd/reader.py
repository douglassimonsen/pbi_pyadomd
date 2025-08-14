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
from typing import TYPE_CHECKING, Any, NamedTuple

import clr  # type: ignore[import-untyped]
import structlog

from .c_sharp_type_mapping import adomd_type_map, convert

logger = structlog.get_logger()


path.append(str(Path(__file__).parent)[2:])
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")  # pyright: ignore reportAttributeAccessIssue
from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
    AdomdUnknownResponseException,
)

if TYPE_CHECKING:
    from types import TracebackType

    from Microsoft.AnalysisServices.AdomdClient import IDataReader


class Description(NamedTuple):
    name: str
    type_code: str


class Reader:
    _reader: "IDataReader"

    def __init__(self, reader: "IDataReader") -> None:
        self._reader = reader

    def __enter__(self) -> "Reader":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: "TracebackType | None",  # noqa: PYI036
    ) -> None:
        self.close()

    def close(self) -> None:
        self._reader.Close()

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

    def fetch_many(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Fetches multiple rows from the last executed query.

        Args:
            limit (int | None): The number of rows to fetch. If None, fetches all rows.

        Returns:
            list[dict[str, Any]]: A list of dictionaries representing the rows.

        """
        if limit is not None:
            return [self.fetch_one() for _ in range(limit) if self.read()]
        return list(self.fetch_stream())

    def fetch_one(self) -> dict[str, Any]:
        """Fetches a single row from the last executed query as a dictionary.

        Returns:
            dict[str, Any]: A dictionary representing the row, with column names as keys

        """
        column_names = self.column_names()
        data = self.fetch_one_tuple()
        return dict(zip(column_names, data, strict=False))

    def fetch_one_tuple(self) -> tuple[Any, ...]:
        """Fetches a single row from the last executed query as a tuple.

        Returns:
            tuple[Any, ...]: A tuple representing the row, with C# values converted
                to their appropriate python types.

        """
        return tuple(
            convert(
                self._reader.GetFieldType(i).ToString(),
                self._reader[i],
                adomd_type_map,
            )
            for i in range(self.field_count)
        )

    def fetch_stream(self) -> Iterator[dict[str, Any]]:
        """Fetches the rows from the last executed query as a stream of dictionaries.

        Note:
            You may need to close the reader after fetching the rows if:

            1. You are using a explicit limit that is shorter than the total number of
            rows in the query result
            2. You are tracing the command associated with the reader

            This is because the trace will not create a query end record (since it
            assumes the client is still reading) without explicitly closing the
            reader. The reader can be closed with `self._reader.Close()`

        Returns:
            Iterator[dict[str, Any]]: An iterator over the rows, represented as
                dictionaries.

        """
        column_names = self.column_names()
        while self.read():
            yield dict(zip(column_names, self.fetch_one_tuple(), strict=False))

    @property
    def field_count(self) -> int:
        return self._reader.FieldCount

    @property
    def is_closed(self) -> bool:
        return self._reader.IsClosed

    def read(self) -> bool:
        try:
            return self._reader.Read()
        except AdomdUnknownResponseException:
            return False

    def read_outer_xml(self) -> str:
        return self._reader.ReadOuterXml()
