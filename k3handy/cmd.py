import sys
import inspect
import logging

from k3proc import command

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

        flag(str or list or tuple): str flags.

            - 'x' or ('raise', ): raise CalledProcessError if return code is not 0
            - 't' or ('tty', ): start sub process in a tty.
            - 'n' or ('none', ): if return code is not 0, return None.
            - 'p' or ('pass', ): do not capture stdin, stdout and stderr.
            - 'o' or ('stdout', ): only return stdout in list of str.
            - '0' or ('oneline', ): only return the first line of stdout.

        options: other options pass to k3proc.command().

    Returns:
        str: first line of stdout.
    """
    dd("cmdf:", cmd, arguments, options)
    dd("flag:", flag)
    mp = {
        'x': 'raise',
        't': 'tty',
        'n': 'none',
        'p': 'pass',
        'o': 'stdout',
        '0': 'oneline',
    }
    if isinstance(flag, str):
        flag = [mp[x] for x in flag]

    if 'raise' in flag:
        options['check'] = True
    if 'tty' in flag:
        options['tty'] = True
    if 'pass' in flag:
        options['capture'] = False

    code, out, err = command(cmd, *arguments, **options)

    # reaching here means there is no check of exception
    if code != 0 and 'none' in flag:
        return None

    out = out.splitlines()
    err = err.splitlines()

    if 'stdout' in flag:
        dd("cmdf: out:", out)
        return out

    if 'oneline' in flag:
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
