import os


def pjoin(*args):
    """
    Alias to os.path.join()

    >>> pjoin("a", "b")
    'a/b'

    >>> pjoin("a", "b", "c")
    'a/b/c'

    """
    return os.path.join(*args)


def pabs(*args):
    """
    Alias to os.path.abspath() and os.path.normpath()

    >>> pabs('a').startswith(os.path.abspath("."))
    True

    >>> pabs('a')[-2:]
    '/a'


    """
    p = os.path.abspath(pjoin(*args))
    return os.path.normpath(p)


def prebase(base, *pseg):
    '''
    Rebaase path pseg on to base and returns the absolute path.

    >>> prebase("/a", "b")
    '/a/b'

    >>> prebase("/a", "b", "c")
    '/a/b/c'

    >>> prebase("/a", "/b")
    '/b'

    >>> prebase("/a", "b/../c")
    '/a/c'

    >>> prebase("/a")
    '/a'

    >>> repr(prebase("a", None))
    'None'

    >>> prebase(None, "/b")
    '/b'

    Args:

        base: base path, aka the left part.

        *pseg: segments to append to ``base``.

    Returns:
        str: the path joined
    '''

    for p in pseg:
        if p is None:
            return None

        if os.path.isabs(p):
            base = p

        if base is None:
            base = pabs(p)

        base = pabs(base, p)

    return base
