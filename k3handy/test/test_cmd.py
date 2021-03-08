import unittest

import k3ut
import k3handy

dd = k3ut.dd


class TestHandyCmd(unittest.TestCase):

    def test_cmdf(self):

        for f in ('0', ('oneline', )):
            got = k3handy.cmdf(
                'python', '-c', 'print("a"); print("b")',
                flag=f
            )
            self.assertEqual('a', got)

            #  no output

            got = k3handy.cmdf(
                'python', '-c', '',
                flag=f
            )
            self.assertEqual('', got)

            # not raise without 'x'
            k3handy.cmdf(
                'python', '-c',
                'import sys; sys.exit(5)',
                flag=f,
            )

        # return None if error

        for f in ('n0', ['none', 'oneline']):
            got = k3handy.cmdf(
                'python', '-c',
                'import sys; sys.exit(5)',
                flag=f,
            )
            self.assertEqual(None, got)

        #  raise with 'x'

        for f in ('x0', ['raise', 'oneline']):
            self.assertRaises(k3handy.CalledProcessError,
                              k3handy.cmdf,
                              'python', '-c',
                              'import sys; sys.exit(5)',
                              flag=f,
                              )

        self.assertRaises(k3handy.CalledProcessError,
                          k3handy.cmdx,
                          'python', '-c',
                          'import sys; sys.exit(5)',
                          )

        # out
        for f in ('o', ['stdout']):

            got = k3handy.cmdf(
                'python', '-c', 'print("a"); print("b")',
                flag=f,
            )
            self.assertEqual(['a', 'b'], got)

        for f in ('xo', ['raise', 'stdout']):
            self.assertRaises(k3handy.CalledProcessError,
                              k3handy.cmdf,
                              'python', '-c',
                              'import sys; sys.exit(5)',
                              flag=f,
                              )

        # tty

        for f in ('t', ['tty']):
            returncode, out, err = k3handy.cmdf(
                'python', '-c', 'import sys; print(sys.stdout.isatty())',
                flag=f,
            )

            dd('out:', out)
            self.assertEqual(['True'], out)

        returncode, out, err = k3handy.cmdtty(
            'python', '-c', 'import sys; print(sys.stdout.isatty())',
        )
        dd('out:', out)
        self.assertEqual(['True'], out)

        # input

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
