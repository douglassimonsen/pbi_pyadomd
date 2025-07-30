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
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from typing import Any, NamedTuple

# Types
F = Callable[[Any], Any]


class TypeCode(NamedTuple):
    type_obj: F
    type_name: str


def _option_type(datatype: type, data: Any) -> Any:
    if data:
        return datatype(data)
    if datatype in {bool, int, float} and data == 0:
        return datatype(data)
    return None


class CDatetime:
    Year: int
    Month: int
    Day: int
    Hour: int
    Minute: int
    Second: int


def conv_dt(x: CDatetime) -> datetime | None:
    return datetime(x.Year, x.Month, x.Day, x.Hour, x.Minute, x.Second, tzinfo=UTC) if x else None


def conv_obj(x: Any) -> Any:
    return x


adomd_type_map: dict[str, TypeCode] = {
    "System.Boolean": TypeCode(partial(_option_type, bool), bool.__name__),
    "System.DateTime": TypeCode(
        conv_dt,
        datetime.__name__,
    ),
    # "System.Decimal": TypeCode(
    #     lambda x: Decimal.ToDouble(x) if x else None, float.__name__  #
    # ),
    "System.Double": TypeCode(partial(_option_type, float), float.__name__),
    "System.Single": TypeCode(partial(_option_type, float), float.__name__),
    "System.String": TypeCode(partial(_option_type, str), str.__name__),
    "System.Guid": TypeCode(partial(_option_type, str), str.__name__),
    "System.UInt16": TypeCode(partial(_option_type, int), int.__name__),
    "System.UInt32": TypeCode(partial(_option_type, int), int.__name__),
    "System.UInt64": TypeCode(partial(_option_type, int), int.__name__),
    "System.Int16": TypeCode(partial(_option_type, int), int.__name__),
    "System.Int32": TypeCode(partial(_option_type, int), int.__name__),
    "System.Int64": TypeCode(partial(_option_type, int), int.__name__),
    "System.Object": TypeCode(conv_obj, "System.Object"),
}


def convert(datatype: str, data: Any, type_map: dict[str, TypeCode]) -> Any:
    type_to_convert = type_map[datatype]
    return type_to_convert.type_obj(data)
