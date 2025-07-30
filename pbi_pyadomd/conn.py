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
from typing import TYPE_CHECKING, Self

import bs4
import clr  # type: ignore[import-untyped]
import structlog

from . import utils
from .Microsoft.AnalysisServices.enums import ConnectionState
from .reader import Reader

logger = structlog.get_logger()


path.append(str(Path(__file__).parent)[2:])
clr.AddReference("Microsoft.AnalysisServices.AdomdClient")  # pyright: ignore reportAttributeAccessIssue
from Microsoft.AnalysisServices.AdomdClient import (  # noqa: E402
    AdomdCommand,
    AdomdConnection,
    AdomdErrorResponseException,
)

__all__ = [
    "AdomdErrorResponseException",
    "Connection",
]  # needed to keep ruff from cleaning up the exception

if TYPE_CHECKING:
    from types import TracebackType


class Connection:
    conn: AdomdConnection
    """The underlying C# AdomdConnection object."""
    reader: Reader
    """The python reader for the connection, used to execute queries."""

    def __init__(self, conn_str: str) -> None:
        self.conn = AdomdConnection(conn_str)

    def clone(self) -> "Connection":
        """Clones the connection."""
        return Connection(self.conn.ConnectionString)

    def close(self) -> None:
        """Closes the connection."""
        self.conn.Close()
        self.conn.Dispose()

    def open(self) -> Self:
        """Opens the connection."""
        self.conn.Open()
        return self

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

    def execute_xml(
        self,
        query: str,
        query_name: str | None = None,
    ) -> bs4.BeautifulSoup:
        query_name = query_name or ""
        logger.debug("execute XML query", query_name=query_name)
        cmd = AdomdCommand(query, self.conn)

        with Reader(cmd.ExecuteXmlReader()) as reader:
            logger.debug("reading query", query_name=query_name)
            lines = [reader.read_outer_xml()]
            while lines[-1] != "":
                lines.append(reader.read_outer_xml())
            ret = bs4.BeautifulSoup("".join(lines), "xml")
            for node in ret.find_all():
                assert isinstance(node, bs4.element.Tag)
                node.name = utils._decode_name(node.name)

        return ret

    def execute_non_query(self, query: str, query_name: str | None = None) -> Self:
        query_name = query_name or ""
        logger.debug("execute DAX query", query_name=query_name)
        cmd = AdomdCommand(query, self.conn)
        cmd.ExecuteNonQuery()
        return self

    def execute_dax(self, query: str, query_name: str | None = None) -> Reader:
        query_name = query_name or ""
        logger.debug("execute DAX query", query_name=query_name)
        cmd = AdomdCommand(query, self.conn)
        return Reader(cmd.ExecuteReader())


def connect(conn_str: str) -> Connection:
    """Connects to the given connection string."""
    return Connection(conn_str)
