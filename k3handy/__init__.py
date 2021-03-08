"""
k3handy is collection of mostly used  utilities.
"""

__version__ = "0.1.5"
__name__ = "k3handy"

import os
import sys
import logging
import inspect

from . import path

from k3proc import command
from k3proc import CalledProcessError
from k3proc import TimeoutExpired
from k3str import to_bytes

from .path import pabs
from .path import pjoin
from .path import prebase

from .cmd import cmd0
from .cmd import cmdf
from .cmd import cmdout
from .cmd import cmdpass
from .cmd import cmdtty
from .cmd import cmdx

from .cmd import dd
from .cmd import ddstack


logger = logging.getLogger(__name__)

#  Since 3.8 there is a stacklevel argument
ddstack_kwarg = {}
if sys.version_info.major == 3 and sys.version_info.minor >= 8:
    ddstack_kwarg = {"stacklevel": 2}


def display(stdout, stderr=None):
    """
    Output to stdout and stderr.
    - ``display(1, "foo")`` write to stdout.
    - ``display(1, ["foo", "bar"])`` write multilines to stdout.
    - ``display(1, ("foo", "bar"))`` write multilines to stdout.
    - ``display(("foo", "bar"), ["woo"])`` write multilines to stdout and stderr.
    - ``display(None, ["woo"])`` write multilines to stderr.

    """

    if isinstance(stdout, int):
        fd = stdout
        line = stderr

        if isinstance(line, (list, tuple)):
            lines = line
            for l in lines:
                display(fd, l)
            return

        os.write(fd, to_bytes(line))
        os.write(fd, b"\n")
        return

    if stdout is not None:
        display(1, stdout)

    if stderr is not None:
        display(2, stderr)
