from collections.abc import Callable, Iterable, Mapping
import threading
from typing import Any
from termui import TerminalUi
from network import NetworkHandler


class MainController(threading.Thread):
    def __init__(self) -> None:
        super(MainController, self).__init__()


if __name__ == "__main__":
    print("hello")
