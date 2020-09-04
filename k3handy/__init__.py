"""
k3handy is collection of mostly used  utilities.
"""

__version__ = "0.1.0"
__name__ = "k3handy"

import os
import sys
import logging
import inspect


from k3proc import command
from k3proc import CalledProcessError
from k3proc import TimeoutExpired
from k3str import to_bytes

logger = logging.getLogger(__name__)

#  Since 3.8 there is a stacklevel argument
ddstack_kwarg = {}
if sys.version_info.major == 3 and sys.version_info.minor >= 8:
    ddstack_kwarg = {"stacklevel": 2}

def dd(*msg):
    """
    Alias to logger.debug()
    """
    msg = [str(x) for x in msg]
    msg = ' '.join(msg)
    logger.debug(msg, **ddstack_kwarg)


def ddstack(*msg):
    """
    Log calling stack in logging.DEBUG level.
    """

    if logger.isEnabledFor(logging.DEBUG):

        stack = inspect.stack()[1:]
        for i, (frame, path, ln, func, line, xx) in enumerate(stack):
            #  python -c "xxx" does not have a line
            if line is None:
                line = ''
            else:
                line = line[0].strip()
            logger.debug("stack: %d %s %s", ln, func, line, **ddstack_kwarg)

def cmdf(cmd, *arguments, flag='', **options):
    """
    Alias to k3proc.command(). Behaviors is specified with ``flag``

    Args:
        cmd(str): the path to executable.

        arguments: arguments

        flag(str): str flags.

            - 'x': raise CalledProcessError if return code is not 0
            - 't': start sub process in a tty.
            - 'n': if return code is not 0, return None.
            - 'p': do not capture stdin, stdout and stderr.
            - 'o': only return stdout in list of str.
            - '0': only return the first line of stdout.

        options: other options pass to k3proc.command().

    Returns:
        str: first line of stdout.
    """
    dd("cmdf:", cmd, arguments, options)
    dd("flag:", flag)

    if 'x' in flag:
        options['check'] = True
    if 't' in flag:
        options['tty'] = True
    if 'p' in flag:
        options['capture'] = False

    code, out, err = command(cmd, *arguments, **options)

    # reaching here means there is no check of exception
    if code != 0 and 'n' in flag:
        return None

    out = out.splitlines()
    err = err.splitlines()

    if 'o' in flag:
        dd("cmdf: out:", out)
        return out

    if '0' in flag:
        dd("cmdf: out:", out)
        if len(out) > 0:
            return out[0]
        return ''

    return code, out, err

def cmd0(cmd, *arguments, **options):
    """
    Alias to k3proc.command() with ``check=True``

    Returns:
        str: first line of stdout.
    """
    dd("cmd0:", cmd, arguments, options)
    _, out, _ = cmdx(cmd, *arguments, **options)
    dd("cmd0: out:", out)
    if len(out) > 0:
        return out[0]
    return ''


def cmdout(cmd, *arguments, **options):
    """
    Alias to k3proc.command() with ``check=True``.

    Returns:
        list: stdout in lines of str.
    """

    dd("cmdout:", cmd, arguments, options)
    _, out, _ = cmdx(cmd, *arguments, **options)
    dd("cmdout: out:", out)
    return out


def cmdx(cmd, *arguments, **options):
    """
    Alias to k3proc.command() with ``check=True``.

    Returns:
        (int, list, list): exit code, stdout and stderr in lines of str.
    """
    dd("cmdx:", cmd, arguments, options)
    ddstack()

    options['check'] = True
    code, out, err = command(cmd, *arguments, **options)
    out = out.splitlines()
    err = err.splitlines()
    return code, out, err


def cmdtty(cmd, *arguments, **options):
    """
    Alias to k3proc.command() with ``check=True`` ``tty=True``.
    As if the command is run in a tty.

    Returns:
        (int, list, list): exit code, stdout and stderr in lines of str.
    """

    dd("cmdtty:", cmd, arguments, options)
    options['tty'] = True
    return cmdx(cmd, *arguments, **options)


def cmdpass(cmd, *arguments, **options):
    """
    Alias to k3proc.command() with ``check=True`` ``capture=False``.
    It just passes stdout and stderr to calling process.

    Returns:
        (int, list, list): exit code and empty stdout and stderr.
    """
    # interactive mode, delegate stdin to sub proc
    dd("cmdpass:", cmd, arguments, options)
    options['capture'] = False
    return cmdx(cmd, *arguments, **options)

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
