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
from pathlib import Path
from sys import path
from typing import TYPE_CHECKING, Any, NamedTuple

import clr
import structlog

from .c_sharp_type_mapping import adomd_type_map, convert

logger = structlog.get_logger()


path.append(str(Path(__file__).parent)[2:])
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")  # pyright: ignore reportAttributeAccessIssue
from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
    AdomdUnknownResponseException,
)

if TYPE_CHECKING:
    from Microsoft.AnalysisServices.AdomdClient import IDataReader


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
