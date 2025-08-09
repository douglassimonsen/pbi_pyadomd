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
from dataclasses import dataclass

import bs4
import structlog

logger = structlog.get_logger()


@dataclass
class XmlaErrorInfo:
    description: str
    error_code: int
    help_file: str | None
    source: str | None

    def __str__(self) -> str:
        return (
            f"Error Code: {self.error_code}\n"
            f"Description: {self.description}\n"
            f"Source: {self.source}\n"
            f"Help File: {self.help_file}"
        )


class XmlaResponseError(Exception):
    """Exception raised for XMLA error responses."""

    def __init__(
        self,
        errors: list[XmlaErrorInfo],
        full_message: bs4.BeautifulSoup,
    ) -> None:
        message = "XMLA error response"
        error_str = "\n\n".join(str(x) for x in errors)
        message += f"\n\n{error_str}"

        super().__init__(message)
        self.errors = errors
        self.full_message = full_message


def check_errors(xml: bs4.BeautifulSoup) -> None:
    errors = [
        XmlaErrorInfo(
            node["Description"],  # pyright: ignore  # noqa: PGH003
            int(node["ErrorCode"]),  # pyright: ignore  # noqa: PGH003
            node["HelpFile"] or None,  # pyright: ignore  # noqa: PGH003
            node["Source"] or None,  # pyright: ignore  # noqa: PGH003
        )
        for node in xml.find_all("Error")
    ]
    if errors:
        raise XmlaResponseError(
            errors,
            xml,
        )
