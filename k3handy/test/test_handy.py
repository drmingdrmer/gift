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
        self.assertEqual("DEBUG:k3handy.cmd:123", got)

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
            "DEBUG:k3handy.cmd:stack: 6 foo ",
            "DEBUG:k3handy.cmd:stack: 7 <module> ",
        ], got)

        got = k3handy.cmdout(
            'python', '-c',
            script.format(level="INFO")
        )
        self.assertEqual([], got)


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
