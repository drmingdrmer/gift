#!/usr/bin/env python
# coding: utf-8


import imp
import os
import unittest

gift = imp.load_source('gift', './gift')

cmdx = gift.cmdx
read_file = gift.read_file
write_file = gift.write_file
pj = gift.pj
dd = gift.dd
_bytes = gift._bytes


# root of this repo
this_base = os.path.dirname(__file__)

giftp = pj(this_base, "gift")
origit = "git"

superp = pj(this_base, "testdata", "super")
subbarp = pj(this_base, "testdata", "super", "foo", "bar")
subwowp = pj(this_base, "testdata", "super", "foo", "wow")


class TestGift(unittest.TestCase):

    def setUp(self):

        force_remove(pj(this_base, "testdata", "super", ".git"))
        cmdx("git", "reset", "testdata", cwd=this_base)
        cmdx("git", "checkout", "testdata", cwd=this_base)
        cmdx("git", "clean", "-dxf", cwd=this_base)

        # .git can not be track in a git repo.
        # need to manually create it.
        write_file(pj(this_base, "testdata", "super", ".git"),
                   "gitdir: ../supergit")

    def tearDown(self):
        force_remove(pj(this_base, "testdata", "super", ".git"))
        cmdx("git", "reset", "testdata", cwd=this_base)
        cmdx("git", "checkout", "testdata", cwd=this_base)
        cmdx("git", "clean", "-dxf", cwd=this_base)

    def test_init(self):
        self._nofile(subbarp, "bar")
        self._nofile(subwowp, "wow")

        for _ in range(2):
            cmdx(giftp, "initsub", cwd=superp)

            self._fcontent("bar\n", subbarp, "bar")
            self._fcontent("wow\n", subwowp, "wow")

            self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subbarp)
            self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subwowp)
            self._gitoutput([giftp, "ls-files"], [".gift", "imsuperman"], cwd=superp)

    def test_commit_super(self):
        cmdx(giftp, "initsub", cwd=superp)
        cmdx(giftp, "add", "foo", cwd=superp)
        cmdx(giftp, "commit", "-m", "add foo", cwd=superp)

        self._gitoutput([giftp, "ls-files"],
                        [
            ".gift",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=superp)

    def test_commitsub(self):
        cmdx(giftp, "initsub", cwd=superp)
        cmdx(giftp, "commitsub", cwd=superp)

        self._gitoutput([giftp, "ls-files"],
                        [
            ".gift",
            ".gift-state",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=superp)

        self._fcontent(
            "\n".join(["- - foo/bar",
                       "  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af",
                       "- - foo/wow",
                       "  - 6bf37e52cbafcf55ff4710bb2b63309b55bf8e54",
                       ""]),
            superp, ".gift-state",
        )

    def test_op_in_sub(self):

        cmdx(giftp, "initsub", cwd=superp)

        _, out, _ = cmdx(origit, "rev-parse", "HEAD", cwd=superp)
        superhash = out[0]
        dd(superhash)

        _, out, _ = cmdx(giftp, "rev-parse", "HEAD", cwd=superp)
        self.assertEqual(superhash, out[0], "gift should get the right super HEAD hash")

        _, out, _ = cmdx(giftp, "rev-parse", "HEAD", cwd=subbarp)
        barhash = out[0]
        self.assertNotEqual(barhash, superhash, "gift should get a different hash in sub dir bar")

        self._add_newbar()

        _, out, _ = cmdx(origit, "rev-parse", "HEAD", cwd=superp)
        superhash2 = out[0]
        self.assertEqual(superhash, superhash2, "commit in sub dir should not change super dir HEAD")

    def test_populate_super_ref(self):

        cmdx(giftp, "initsub", cwd=superp)

        cmdx(giftp, "commitsub", cwd=superp)

        self._add_newbar()
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subbarp)
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subwowp)

        # initsub should populate super/head
        cmdx(giftp, "initsub", cwd=superp)
        self._check_initial_superhead()

    def _check_initial_superhead(self):
        _, out, _ = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", out[0])

        _, out, _ = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subwowp)
        self.assertEqual("6bf37e52cbafcf55ff4710bb2b63309b55bf8e54", out[0])

    def _add_newbar(self):
        write_file(pj(subbarp, "newbar"), "newbar")
        cmdx(giftp, "add", "newbar", cwd=subbarp)
        cmdx(giftp, "commit", "-m", "add newbar", cwd=subbarp)

        # TODO test no .gift file

    def _gitoutput(self, cmds, lines, **kwargs):
        _, out, _ = cmdx(*cmds, **kwargs)
        self.assertEqual(lines, out)

    def _nofile(self, *ps):
        self.assertFalse(os.path.isfile(pj(*ps)), "no file in " + pj(*ps))

    def _fcontent(self, txt, *ps):
        self.assertTrue(os.path.isfile(pj(*ps)), pj(*ps) + " should exist")

        actual = read_file(pj(*ps))
        self.assertEqual(txt, actual, "check file content")


def force_remove(fn):

    try:
        os.rmdir(fn)
    except BaseException:
        pass

    try:
        os.unlink(fn)
    except BaseException:
        pass
