import os
import unittest

import k3ut
import k3handy

dd = k3ut.dd

class TestHandyLogging(unittest.TestCase):

    def test_dd(self):
        script = '''
import sys;
import logging;
import k3handy;
logging.basicConfig(stream=sys.stdout, level=logging.{level});
k3handy.dd("123");
'''
        got = k3handy.cmd0(
            'python', '-c',
            script.format(level="DEBUG")
        )
        self.assertEqual("DEBUG:k3handy:123", got)

        got = k3handy.cmd0(
            'python', '-c',
            script.format(level="INFO")
        )
        self.assertEqual("", got)

    def test_ddstack(self):
        script = '''
import sys;
import logging;
import k3handy;
logging.basicConfig(stream=sys.stdout, level=logging.{level});
def foo(): k3handy.ddstack("123");
foo()
'''
        got = k3handy.cmdout(
            'python', '-c',
            script.format(level="DEBUG")
        )
        self.assertEqual([
                "DEBUG:k3handy:stack: 6 foo ",
                "DEBUG:k3handy:stack: 7 <module> ",
        ], got)

        got = k3handy.cmdout(
            'python', '-c',
            script.format(level="INFO")
        )
        self.assertEqual([], got)

class TestHandyCmd(unittest.TestCase):

    def test_cmdf(self):

        got = k3handy.cmdf(
            'python', '-c', 'print("a"); print("b")',
                flag='0'
        )
        self.assertEqual('a', got)

        #  no output

        got = k3handy.cmdf(
            'python', '-c', '',
                flag='0'
        )
        self.assertEqual('', got)


        # not raise without 'x'
        k3handy.cmdf(
                'python', '-c',
                'import sys; sys.exit(5)',
                flag='0',
        )

        # return None if error
        got = k3handy.cmdf(
                'python', '-c',
                'import sys; sys.exit(5)',
                flag='n0',
        )
        self.assertEqual(None, got)

        #  raise with 'x'
        self.assertRaises(k3handy.CalledProcessError,
                          k3handy.cmdf,
                          'python', '-c',
                          'import sys; sys.exit(5)',
                          flag='x0',
                          )

        # out

        got = k3handy.cmdf(
            'python', '-c', 'print("a"); print("b")',
                flag='o',
        )
        self.assertEqual(['a', 'b'], got)

        self.assertRaises(k3handy.CalledProcessError,
                          k3handy.cmdf,
                          'python', '-c',
                          'import sys; sys.exit(5)',
                          flag='xo',
                          )

        # tty

        returncode, out, err = k3handy.cmdf(
            'python', '-c', 'import sys; print(sys.stdout.isatty())',
                flag='t',
        )

        dd('out:', out)
        self.assertEqual(['True'], out)

        read_stdin_in_subproc = '''
import k3handy;
k3handy.cmdf(
'python', '-c', 'import sys; print(sys.stdin.read())',
flag='p'
)
        '''

        returncode, out, err = k3handy.cmdx(
            'python', '-c',
            read_stdin_in_subproc,
            input="123",
        )

        dd('out:', out)
        self.assertEqual(["123"], out)


    def test_cmd0(self):
        got = k3handy.cmd0(
            'python', '-c', 'print("a"); print("b")',
        )
        self.assertEqual('a', got)

        #  no output

        got = k3handy.cmd0(
            'python', '-c', '',
        )
        self.assertEqual('', got)

        #  failure to exception

        self.assertRaises(k3handy.CalledProcessError,
                          k3handy.cmd0,
                          'python', '-c',
                          'import sys; sys.exit(5)',
                          )

    def test_cmdout(self):
        got = k3handy.cmdout(
            'python', '-c', 'print("a"); print("b")',
        )
        self.assertEqual(['a', 'b'], got)

        self.assertRaises(k3handy.CalledProcessError,
                          k3handy.cmdout,
                          'python', '-c',
                          'import sys; sys.exit(5)',
                          )
    def test_cmdx(self):
        got = k3handy.cmdx(
            'python', '-c', 'print("a"); print("b")',
        )
        self.assertEqual((0, ['a', 'b'], []), got)

        self.assertRaises(k3handy.CalledProcessError,
                          k3handy.cmdx,
                          'python', '-c',
                          'import sys; sys.exit(5)',
                          )

    def test_cmdtty(self):
        returncode, out, err = k3handy.cmdtty(
            'python', '-c', 'import sys; print(sys.stdout.isatty())',
        )

        dd('returncode:', returncode)
        dd('out:', out)
        dd('err:', err)

        self.assertEqual(0, returncode)
        self.assertEqual(['True'], out)
        self.assertEqual([], err)

    def test_cmdpass(self):
        read_stdin_in_subproc = '''
import k3handy;
k3handy.cmdpass(
'python', '-c', 'import sys; print(sys.stdin.read())',
)
        '''

        returncode, out, err = k3handy.cmdx(
            'python', '-c',
            read_stdin_in_subproc,
            input="123",
        )

        dd('returncode:', returncode)
        dd('out:', out)
        dd('err:', err)

        self.assertEqual(0, returncode)
        self.assertEqual(["123"], out)


class TestHandyDisplay(unittest.TestCase):

    def test_display(self):

        for cmd, want in (
                ('display(1, "foo")', (["foo"], [])),
                ('display(2, "foo")', ([], ["foo"])),
                ('display(2, ["foo", "bar"])', ([], ["foo", "bar"])),
                ('display(None, ["foo", "bar"])', ([], ["foo", "bar"])),
                ('display(["foo", "bar"], None)', (["foo", "bar"], [])),
                ('display(["foo", "bar"])', (["foo", "bar"], [])),
                ('display(["foo", "bar"], ["woo"])', (["foo", "bar"], ["woo"])),
                ('display("foo", "bar")', (["foo"], ["bar"])),
        ):

            _, out, err = k3handy.cmdx(
                'python', '-c',
                'import k3handy; k3handy.{}'.format(cmd),
            )

            self.assertEqual(want, (out, err))
