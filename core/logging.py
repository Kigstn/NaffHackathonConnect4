import dataclasses
import logging
import os
import time
from typing import Optional

from naff import logger_name
from rich.highlighter import Highlighter
from rich.logging import RichHandler
from rich.text import Text


@dataclasses.dataclass
class ColourHighlighter(Highlighter):
    name: str = "Other"
    colour: str = "yellow"

    # noinspection PyProtectedMember
    def highlight(self, text: Text):
        plain = text.plain

        # make code blocks nicer
        result = []
        first = True
        for char in plain:
            if char == "`":
                result.append("[bold][italic]" if first else "[/bold][/italic]")
                first = not first
            else:
                result.append(char)
        plain = "".join(result)

        new_text = Text.assemble(
            (f"[{self.name.upper()}] ", self.colour), Text.from_markup(plain)
        )
        text._text = new_text._text
        text._spans = new_text._spans
        text._length = new_text._length


class CustomLogger:
    """Log all errors to a file, and log all logging events to console"""

    @staticmethod
    def make_console_logger(
        logger: logging.Logger,
        highlighter: Optional[Highlighter] = None,
        level: int = logging.DEBUG,
    ):
        logger.propagate = False
        console_handler = RichHandler(
            show_time=True,
            omit_repeated_times=False,
            show_level=True,
            show_path=True,
            enable_link_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            log_time_format="[%d/%m/%Y %H:%M:%S]",
            level=level,
            highlighter=highlighter,
        )
        logger.handlers = []
        logger.addHandler(console_handler)

    def make_logger(self, log_name: str, only_console: bool = False):
        logger = logging.getLogger(log_name)
        logger.setLevel(logging.DEBUG)

        # log to console (DEBUG)
        self.make_console_logger(
            logger=logger,
            highlighter=ColourHighlighter(name=log_name.upper(), colour="#71b093"),
        )

        # log to file (INFO)
        if not only_console:
            file_handler = MakeFileHandler(
                filename=f"./logs/{log_name}.log",
                encoding="utf-8",
            )
            file_formatter = logging.Formatter(
                "%(asctime)s UTC || %(levelname)s || %(message)s"
            )
            file_formatter.converter = time.gmtime
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)


class MakeFileHandler(logging.FileHandler):
    """Subclass of logging.FileHandler which makes sure the folder is created"""

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        encoding: Optional[str] = None,
        delay: bool = False,
    ):
        # create the folder if it does not exist already
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        super().__init__(filename, mode, encoding, delay)


def init_logging():
    # Initialize formatter
    logger = CustomLogger()

    logger.make_logger("NAFF")
    logger.make_logger("Connect4")
