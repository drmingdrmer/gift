"""
k3str is a collection of string operation utilily.

>>> repr(to_bytes('我'))
"b'\\\\xe6\\\\x88\\\\x91'"

"""

__version__ = "0.1.1"
__name__ = "k3str"

from .str_ext import (
    default_encoding,
    to_bytes,
    to_utf8,
)

__all__ = [
    'default_encoding',
    'to_bytes'
    'to_utf8',
]
