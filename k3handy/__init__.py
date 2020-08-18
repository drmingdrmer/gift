"""
k3handy is collection of mostly used  utilities.
"""

__version__ = "0.1.0"
__name__ = "k3handy"

import sys
import logging
import inspect


from k3proc import command
from k3proc import CalledProcessError
from k3proc import TimeoutExpired

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
