import sys

default_encoding = sys.getdefaultencoding()
if hasattr(sys, 'getfilesystemencoding'):
    default_encoding = sys.getfilesystemencoding()


def to_utf8(s):
    """
    Convert str to utf8 bytes.
    It is an alias of ``to_bytes(s, encoding='utf-8')``.
    """
    return to_bytes(s, encoding='utf-8')


def to_bytes(s, encoding=None):
    """
    Convert str to bytes.  If it is already bytes, do nothing.

    Args:

        s: str or bytes

        encoding(str):
            the encoding to encode str.
            If it is None, system default encoding is used.

    Returns:
        bytes
    """

    if encoding is None:
        encoding = default_encoding

    if isinstance(s, bytes):
        return s

    if isinstance(s, str):
        return bytes(s, encoding)

    return bytes(str(s), encoding)
