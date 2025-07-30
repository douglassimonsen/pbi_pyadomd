from enum import Enum


class ConnectionState(Enum):
    Closed = 0
    Open = 1
    Connecting = 2
    Executing = 4
    Fetching = 8
    Broken = 16
