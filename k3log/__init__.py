"""
k3log is a collection of log utilities for logging.
"""

from .log import (
    add_std_handler,
    deprecate,
    get_datefmt,
    get_fmt,
    get_root_log_fn,
    make_file_handler,
    make_formatter,
    make_logger,
    set_logger_level,
    stack_format,
    stack_list,
    stack_str,
)

#  from .archive import(
#      Archiver,

#      archive,
#      clean,
#  )

__version__ = "0.1.3"
__name__ = "k3log"

__all__ = [
    "add_std_handler",
    "deprecate",
    "get_datefmt",
    "get_fmt",
    "get_root_log_fn",
    "make_file_handler",
    "make_formatter",
    "make_logger",
    "set_logger_level",
    "stack_format",
    "stack_list",
    "stack_str",
]
