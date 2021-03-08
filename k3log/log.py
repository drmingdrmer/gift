import errno
import logging
import logging.handlers
import os
import sys
import traceback
from stat import ST_DEV
from stat import ST_INO

import __main__
import k3confloader

logger = logging.getLogger(__name__)

log_formats = {
    'default': '[%(asctime)s,%(process)d-%(thread)d,%(filename)s,%(lineno)d,%(levelname)s] %(message)s',
    'time_level': "[%(asctime)s,%(levelname)s] %(message)s",
    'message': '%(message)s',

    # more info: but it is too long.
    # 'full': '[%(asctime)s,%(process)d-%(thread)d,%(name)s, %(filename)s,%(lineno)d,%(funcName)s %(levelname)s] %(message)s',
}

date_formats = {
    # by default do not specify
    'default': None,
    'time': '%H:%M:%S',
}

log_suffix = 'out'

default_stack_sep = ' --- '


class FixedWatchedFileHandler(logging.FileHandler):
    """
    A handler for logging to a file, which watches the file
    to see if it has changed while in use. This can happen because of
    usage of programs such as newsyslog and logrotate which perform
    log file rotation. This handler, intended for use under Unix,
    watches the file to see if it has changed since the last emit.
    (A file has changed if its device or inode have changed.)
    If it has changed, the old file stream is closed, and the file
    opened to get a new stream.

    This handler is not appropriate for use under Windows, because
    under Windows open files cannot be moved or renamed - logging
    opens the files with exclusive locks - and so there is no need
    for such a handler. Furthermore, ST_INO is not supported under
    Windows; stat always returns zero for this value.

    This handler is based on a suggestion and patch by Chad J.
    Schroeder.
    """

    def __init__(self, filename, mode='a', encoding=None, delay=0, tag=None):
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)
        self.dev, self.ino = -1, -1
        self.tag = tag
        self._statstream()

    def _statstream(self):
        if self.stream:
            sres = os.fstat(self.stream.fileno())
            self.dev, self.ino = sres[ST_DEV], sres[ST_INO]

    def emit(self, record):
        """
        Emit a record.

        First check if the underlying file has changed, and if it
        has, close the old stream and reopen the file to get the
        current stream.
        """
        # Reduce the chance of race conditions by stat'ing by path only
        # once and then fstat'ing our new fd if we opened a new log stream.
        # See issue #14632: Thanks to John Mulligan for the problem report
        # and patch.
        try:
            # stat the file by path, checking for existence
            sres = os.stat(self.baseFilename)
        except OSError as e:
            if e.errno == errno.ENOENT:
                sres = None
            else:
                raise
        # compare file system stat with that of our stream file handle
        if not sres or sres[ST_DEV] != self.dev or sres[ST_INO] != self.ino:

            # Fixed by xp 2017 Apr 03:
            #     os.fstat still gets OSError(errno=2), although it operates
            #     directly on fd instead of path.  The same for stream.flush().
            #     Thus we keep on trying this close/open/stat loop until no
            #     OSError raises.

            for ii in range(16):
                try:
                    if self.stream is not None:
                        # we have an open file handle, clean it up
                        self.stream.flush()
                        self.stream.close()
                        # See Issue #21742: _open () might fail.
                        self.stream = None
                        # open a new file handle and get new stat info from
                        # that fd
                        self.stream = self._open()
                        self._statstream()
                        break
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        continue
                    else:
                        raise
        logging.FileHandler.emit(self, record)


def get_root_log_fn():
    """
    Returns the log file name for root logger.
    The log file name suffix is ``.out``.

    -   ``pyfn.out``: if program is started with ``python pyfn.py``.
    -   ``__instant_command__.out``: if instance python command is called:
        ``python -c "import k3log; print k3log.get_root_log_fn()``.
    -   ``__stdin__.out``: if python statement is passed in as stdin:
        ``echo "from pykit import k3log; print k3log.get_root_log_fn()" | python``.

    Returns:
        log file name.
    """

    if hasattr(__main__, '__file__'):
        name = __main__.__file__
        name = os.path.basename(name)
        if name == '<stdin>':
            name = '__stdin__'
        return name.rsplit('.', 1)[0] + '.' + log_suffix
    else:
        return '__instant_command__.' + log_suffix


def make_logger(base_dir=None, log_name=None, log_fn=None,
                level=logging.DEBUG, fmt=None,
                datefmt=None):
    """
    It creates a logger with a rolling file hander and specified formats.

    Args:

        base_dir:
            specifies the dir of log file.
            If it is ``None``, use ``config.log_dir`` as default.

        log_name:
            is the name of the logger to create.
            ``None`` means the root logger.

        log_fn:
            specifies the log file name.
            If it is ``None``, use ``k3log.get_root_log_fn`` to make a log file name.

        level:
            specifies log level.
            It could be int value such as ``logging.DEBUG`` or string such as ``DEBUG``.

        fmt:
            specifies log format.
            It can be an alias that can be used in ``k3log.get_fmt()``, or ``None`` to
            used the ``default`` log format.

        datefmt:
            specifies log date format.
            It can be an alias that can be used in ``k3log.get_datefmt()``, or ``None`` to
            used the `default` date format.

    Returns:
        a ``logging.Logger`` instance.

    """

    # if log_name is None, get the root logger
    logger = logging.getLogger(log_name)
    logger.setLevel(level)

    if base_dir is None:
        base_dir = k3confloader.conf.log_dir

    if log_fn is None:
        if log_name is None:
            log_fn = get_root_log_fn()
        else:
            log_fn = log_name + '.' + log_suffix

    #  # do not add 2 handlers to one logger by default
    for h in logger.handlers:
        if getattr(h, "tag", None) == 'root':
            logger.handlers.remove(h)

    logger.addHandler(make_file_handler(base_dir, log_fn,
                                        fmt=fmt, datefmt=datefmt, tag="root"))

    return logger


def make_file_handler(base_dir=None, log_fn=None, fmt=None, datefmt=None, tag=None):
    """
    It creates a rolling log file handler.

    A rolling file can be removed at any time.
    This handler checks file status everytime write log to it.
    If file is changed(removed or moved), this handler automatically creates a new
    log file.

    Args:

        base_dir:
            specifies the dir of log file.
            If it is ``None``, use ``k3conf.log_dir`` as default.

        log_fn:
            specifies the log file name.
            If it is ``None``, use ``k3log.get_root_log_fn`` to make a log file name.

        fmt:
            specifies log format.
            It can be an alias that can be used in ``k3log.get_fmt()``, or ``None`` to
            used the ``default`` log format.

        datefmt:
            specifies log date format.
            It can be an alias that can be used in ``k3log.get_datefmt()``, or ``None`` to
            used the ``default`` date format.

    Returns:
        an instance of `logging.handlers.WatchedFileHandler`.

    """
    if base_dir is None:
        base_dir = k3confloader.conf.log_dir
    if log_fn is None:
        log_fn = get_root_log_fn()
    file_path = os.path.join(base_dir, log_fn)

    handler = FixedWatchedFileHandler(file_path, tag=tag)
    handler.setFormatter(make_formatter(fmt=fmt, datefmt=datefmt))

    return handler


def set_logger_level(level=logging.INFO, name_prefixes=None):
    """
    Set all logger level that matches ``name_prefixes``.

    Args:

        level:
            specifies log level.
            It could be int value such as ``logging.DEBUG`` or string such as ``DEBUG``.

        name_prefixes:
            specifies log prefixes which is operated.
            It can be None, str or a tuple of str.
            If `name_prefixes` is None, set the log level for all logger.
    """

    if name_prefixes is None:
        name_prefixes = ('',)

    root_logger = logging.getLogger()

    loggers = sorted(root_logger.manager.loggerDict.items())

    for name, _ in loggers:
        if name.startswith(name_prefixes):
            name_logger = logging.getLogger(name)
            name_logger.setLevel(level)


def add_std_handler(logger, stream=None, fmt=None, datefmt=None, level=None):
    """
    It adds a `stdout` or `stderr` steam handler to the `logger`.

    Args:

        logger:
            is an instance of `logging.Logger` to add handler to.

        stream:
            specifies the stream, it could be:
            -   ``sys.stdout`` or a string ``stdout``.
            -   ``sys.stderr`` or a string ``stderr``.

        fmt(str):
            is the log message format.
            It can be an alias name(like `default`) that can be used in
            ``get_fmt()``.
            By default it is ``default``:
            ``[%(asctime)s,%(process)d-%(thread)d,%(filename)s,%(lineno)d,%(levelname)s] %(message)s``.

        datefmt(str):
            is the format for date.
            It can be an alias name(like `time`) that can be used in
            `get_datefmt()`.
            By default it is `None`.

        level:
            is the log level.
            It can be int value such as ``logging.DEBUG`` or string such as ``DEBUG``.
            By default it is the logger's level.

    Returns:
        the `logger` in argument.
    """

    stream = stream or sys.stdout

    if stream == 'stdout':
        stream = sys.stdout

    elif stream == 'stderr':
        stream = sys.stderr

    stdhandler = logging.StreamHandler(stream)
    stdhandler.setFormatter(make_formatter(fmt=fmt, datefmt=datefmt))
    if level is not None:
        stdhandler.setLevel(level)

    logger.addHandler(stdhandler)

    return logger


def make_formatter(fmt=None, datefmt=None):
    """
    It creates an `logging.Formatter` instance, with specified `fmt` and `datefmt`.

    Args:

        fmt:
            specifies log format.
            It can be an alias that can be used in `get_fmt()`, or `None` to
            used the `default` log format.

        datefmt:
            specifies log date format.
            It can be an alias that can be used in `get_datefmt()`, or `None` to
            used the `default` date format.

    Returns:
        an `logging.Formatter` instance.
    """

    fmt = get_fmt(fmt)
    datefmt = get_datefmt(datefmt)

    return logging.Formatter(fmt=fmt, datefmt=datefmt)


def get_fmt(fmt):
    """
    It translate a predefined fmt alias to actual fmt.
    Predefined alias includes::

        {
            'default':    '[%(asctime)s,%(process)d-%(thread)d,%(filename)s,%(lineno)d,%(levelname)s] %(message)s',
            'time_level': "[%(asctime)s,%(levelname)s] %(message)s",
            'message':    '%(message)s',
        }

    Args:

        fmt:
            is the alias name.
            If no predefined alias name is found, it returns the passed in value of
            `fmt`.

    Returns:
        translated `fmt` or the original value of argument `fmt`.
    """

    if fmt is None:
        fmt = 'default'

    return log_formats.get(fmt, fmt)


def get_datefmt(datefmt):
    """
    It translates a predefined datefmt alias to actual datefmt.
    Predefined alias includes::

        {
            'default':  None,       # use the system default datefmt
            'time':     '%H:%M:%S',
        }

    Args:

        datefmt:
            is the alias name.
            If no predefined alias name is found, it returns the passed in value of
            `datefmt`.

    Returns:
        translated `datefmt` or the original value of argument `datefmt`.
    """

    if datefmt is None:
        return datefmt

    return date_formats.get(datefmt, datefmt)


def stack_list(offset=0):
    """
    It returns the calling stack from where it is called.

    Args:

        offset:
            remove the lowest `offset` frames.

    Returns:
        list of::

            {
                'fn': ...
                'ln': ...
                'func': ...
                'statement': ...
            }
    """

    offset += 1  # count this function as 1

    # list of ( filename, line-nr, in-what-function, statement )
    x = traceback.extract_stack()
    return x[: -offset]


def stack_format(stacks, fmt=None, sep=None):
    """
    It formats stack made from ``k3log.stack_list``.

    With ``fmt="{fn}:{ln} in {func}\\n  {statement}"``
    and ``sep="\\n"``, a formatted stack would be::

        runpy.py:174 in _run_module_as_main
          "__main__", fname, loader, pkg_name)
        runpy.py:72 in _run_code
          exec code in run_globals
        ...
        test_logutil.py:82 in test_deprecate
          k3log.deprecate()
          'foo', fmt='{fn}:{ln} in {func}\\n  {statement}', sep='\\n')

    Args:

        stacks:
            is stack from ``k3log.stack_list``::

                [
                    {
                        'fn': ...
                        'ln': ...
                        'func': ...
                        'statement': ...
                    }
                    ...
                ]

        fmt:
            specifies the template to format a stack frame.
            By default it is: ``{fn}:{ln} in {func} {statement}``.

        sep:
            specifies the separator string between each stack frame.
            By default it is ``" --- "``.
            Thus all frames are in the same line.

    Returns:
        a string repesenting a calling stack.
    """

    if fmt is None:
        fmt = "{fn}:{ln} in {func} {statement}"

    if sep is None:
        sep = default_stack_sep

    dict_stacks = []
    for st in stacks:
        o = {
            'fn': os.path.basename(st[0]),
            'ln': st[1],
            'func': st[2],
            'statement': st[3],
        }
        dict_stacks.append(o)

    return sep.join([fmt.format(**xx)
                     for xx in dict_stacks])


def stack_str(offset=0, fmt=None, sep=None):
    """
    It creates a string representing calling stack from where this function is
    called.

    Args:

        offset:
            remove the lowest `offset` frames.
            Because usually one does not need the frame of the `k3log.stack_str`
            line.

        fmt: is same as `k3log.stack_format`.

        sep: is same as `k3log.stack_format`.

    Returns:
        a string repesenting a calling stack.
    """
    offset += 1  # count this function as 1
    return stack_format(stack_list(offset), fmt=fmt, sep=sep)


def deprecate(msg=None, fmt=None, sep=None):
    '''
    Print a `deprecate` message, at warning level.
    The printed message includes:

    -   User defined message `msg`,
    -   And calling stack of where this warning occurs.
        `<frame-n>` is where `deprecate` is called.

    ::

        <msg> Deprecated: <frame-1> --- <frame-2> --- ... --- <frame-n>

    The default frame format is `{fn}:{ln} in {func} {statement}`.
    It can be changed with argument `fmt`.
    Frame separator by default is ` --- `, and can be changed with argument `sep`.

    For example, the following statement::

        def foo():
            deprecate('should not be here.',
                      fmt="{fn}:{ln} in {func}\\n  {statement}",
                      sep="\\n"
                      )

    Would produce a message::

        Deprecated: should not be here.
        runpy.py:174 in _run_module_as_main
          "__main__", fname, loader, pkg_name)
        runpy.py:72 in _run_code
          exec code in run_globals
        ...
        test_log.py:82 in test_deprecate
          deprecate()
          'foo', fmt='{fn}:{ln} in {func}\\n  {statement}', sep='\\n')

    Args:

        msg:
            is description of the `deprecated` statement.
            It could be `None`.

        fmt:
            is call stack frame format.
            By default it is `{fn}:{ln} in {func} {statement}`.

        sep:
            is the separator string between each frame.
            By default it is ``" --- "``.
            Thus all frames are printed in a single line.
    '''

    d = 'Deprecated:'

    if msg is not None:
        d += ' ' + str(msg)

    logger.warning(d + (sep or default_stack_sep)
                   + stack_str(offset=1, fmt=fmt, sep=sep))
