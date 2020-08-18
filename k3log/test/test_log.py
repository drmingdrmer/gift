import errno
import logging
import os
import threading
import unittest

import k3log
import k3proc

logger = logging.getLogger(__name__)

this_base = os.path.dirname(__file__)


def subproc(script, cwd=None):
    code, out, err = k3proc.shell_script(script,
                                         close_fds=True,
                                         cwd=cwd
                                         )

    if code != 0:
        print(out)
        print(err)

    return (code, out, err)


def read_file(fn):
    with open(fn, 'r') as f:
        return f.read()


def rm_file(fn):
    try:
        os.unlink(fn)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise


class TestFileHandler(unittest.TestCase):

    def test_concurrent_write_and_remove(self):

        l = k3log.make_logger(base_dir=this_base,
                              log_name='rolling',
                              log_fn='rolling.out',
                              level=logging.DEBUG,
                              fmt='message')

        n = 10240
        sess = {'running': True}

        def _remove():
            while sess['running']:
                rm_file(this_base + '/rolling.out')

        th = threading.Thread(target=_remove)
        th.daemon = True
        th.start()

        for ii in range(n):
            l.debug('123')

        sess['running'] = False
        th.join()


class TestLogutil(unittest.TestCase):

    def setUp(self):

        rm_file(this_base + '/t.out')

        # root logger
        k3log.make_logger(base_dir=this_base,
                          log_fn='t.out',
                          level=logging.DEBUG,
                          fmt='message')

    def test_get_root_log_fn(self):

        # instant

        code, out, err = subproc(
            'python -c "import k3log; print(k3log.get_root_log_fn())"')
        self.assertEqual(0, code)
        self.assertEqual('__instant_command__.out', out.strip())

        code, out, err = subproc(
            'echo "import k3log; print(k3log.get_root_log_fn())" | python')
        self.assertEqual(0, code)
        self.assertEqual('__stdin__.out', out.strip())

        # load by file

        code, out, err = subproc(
            'python foo.py', cwd=os.path.dirname(__file__))
        self.assertEqual(0, code)
        self.assertEqual('foo.out', out.strip())

    def test_deprecate(self):

        fmt = '{fn}::{ln} in {func}\n  {statement}'
        k3log.deprecate('foo', fmt=fmt, sep='\n')

        cont = read_file(this_base + '/t.out')

        self.assertRegex(
            cont,
            '^Deprecated: foo')
        self.assertRegex(
            cont,
            'test_log.py::\d+ in test_deprecate\n  k3log.deprecate')

    def test_stack_list(self):

        stack = k3log.stack_list()
        last = stack[-1]

        self.assertEqual('test_log.py', os.path.basename(last[0]))
        self.assertTrue(isinstance(last[1], int))
        self.assertEqual('test_stack_list', last[2])
        self.assertRegex(last[3], '^ *stack = ')

    def test_format_stack(self):

        cases = (
            ([('0', 1, 2, 3)], '0-1-2-3'),
            ([('0', 1, 2, 3),
              ('a', 'b', 'c', 'd')], '0-1-2-3\na-b-c-d'),
        )

        for inp, expected in cases:

            rst = k3log.stack_format(
                inp, fmt='{fn}-{ln}-{func}-{statement}', sep='\n')
            self.assertEqual(expected, rst)

    def test_stack_str(self):

        rst = k3log.stack_str(fmt='{fn}-{ln}-{func}-{statement}', sep=' ')
        self.assertRegex(
            rst,
            ' test_log.py-\d+-test_stack_str- *rst = ')

    def test_get_datefmt(self):

        cases = (
                (None, None),
                ('default', None),
                ('time', '%H:%M:%S'),
                ('%H%M%S', '%H%M%S'),
        )

        for inp, expected in cases:
            rst = k3log.get_datefmt(inp)

            self.assertEqual(expected, rst)

    def test_get_fmt(self):

        cases = (
                (None,
                 '[%(asctime)s,%(process)d-%(thread)d,%(filename)s,%(lineno)d,%(levelname)s] %(message)s'),
                ('default',
                 '[%(asctime)s,%(process)d-%(thread)d,%(filename)s,%(lineno)d,%(levelname)s] %(message)s'),
                ('time_level', "[%(asctime)s,%(levelname)s] %(message)s"),
                ('message', '%(message)s'),
                ('%(message)s', '%(message)s'),
        )

        for inp, expected in cases:
            rst = k3log.get_fmt(inp)
            self.assertEqual(expected, rst)

    def test_make_logger(self):

        rm_file(this_base + '/tt')

        l = k3log.make_logger(base_dir=this_base,
                              log_name='m',
                              log_fn='tt',
                              level='INFO',
                              fmt='%(message)s',
                              datefmt='%H%M%S'
                              )

        l.debug('debug')
        l.info('info')

        cont = read_file(this_base + '/tt').strip()

        self.assertEqual(cont, 'info')

    def test_make_logger_with_config(self):

        code, out, err = subproc(
            'python make_logger_with_config.py', cwd=os.path.dirname(__file__))
        self.assertEqual(0, code)
        self.assertEqual(out.strip(), 'info')

    def test_make_formatter(self):
        # how to test logging.Formatter?
        pass

    def test_make_file_handler(self):

        rm_file(this_base + '/handler_change')

        l = k3log.make_logger(base_dir=this_base,
                              log_name='h',
                              log_fn='dd',
                              level='INFO',
                              fmt='%(message)s',
                              datefmt='%H%M%S'
                              )
        l.handlers = []
        handler = k3log.make_file_handler(base_dir=this_base,
                                          log_fn='handler_change',
                                          fmt='%(message)s',
                                          datefmt='%H%M%S')
        l.addHandler(handler)

        l.debug('debug')
        l.info('info')

        cont = read_file(this_base + '/handler_change').strip()

        self.assertEqual(cont, 'info')

    def test_make_file_handler_with_config(self):

        code, out, err = subproc(
            'python make_file_handler_with_config.py', cwd=os.path.dirname(__file__))
        self.assertEqual(0, code)
        self.assertEqual(out.strip(), 'info')

    def test_add_std_handler(self):
        rm_file(this_base + '/stdlog')

        code, out, err = subproc(
            'python stdlog.py', cwd=os.path.dirname(__file__))
        self.assertEqual(0, code)
        self.assertEqual('error', out.strip())

    def test_set_logger_level(self):

        cases = (
            (None, 'debug1\ndebug2'),
            ('1_prefix', 'debug1\ndebug2\ndebug2'),
            (('1_prefix', '2_prefix'), 'debug1\ndebug2'),
            (('not_exist',), 'debug1\ndebug2\ndebug1\ndebug2'),
            (('not_exist', '1_prefix'), 'debug1\ndebug2\ndebug2'),
        )

        for inp, expected in cases:
            rm_file(this_base + '/ss')

            logger1 = k3log.make_logger(base_dir=this_base,
                                        log_name='1_prefix_1',
                                        log_fn='ss',
                                        level='DEBUG',
                                        fmt='%(message)s',
                                        datefmt='%H%M%S')

            logger2 = k3log.make_logger(base_dir=this_base,
                                        log_name='2_prefix_1',
                                        log_fn='ss',
                                        level='DEBUG',
                                        fmt='%(message)s',
                                        datefmt='%H%M%S')
            logger1.debug('debug1')
            logger2.debug('debug2')

            k3log.set_logger_level(level='INFO', name_prefixes=inp)

            logger1.debug('debug1')
            logger2.debug('debug2')

            content = read_file(this_base + '/ss')

            self.assertEqual(expected, content.strip())
