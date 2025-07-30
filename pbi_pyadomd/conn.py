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
from typing import TYPE_CHECKING, Self, TypeVar

import clr  # type: ignore[import-untyped]
import structlog

from .cursor import Cursor
from .Microsoft.AnalysisServices.enums import ConnectionState

logger = structlog.get_logger()
T = TypeVar("T")


path.append(str(Path(__file__).parent)[2:])
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")  # pyright: ignore reportAttributeAccessIssue
from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
    AdomdConnection,
    AdomdErrorResponseException,
)

__all__ = [
    "AdomdErrorResponseException",
    "Conn",
]  # needed to keep ruff from cleaning up the exception

if TYPE_CHECKING:
    from types import TracebackType


class Conn:
    def __init__(self, conn_str: str) -> None:
        self.conn = AdomdConnection(conn_str)

    def clone(self) -> "Conn":
        """Clones the connection."""
        return Conn(self.conn.ConnectionString)

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
