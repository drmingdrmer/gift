#!/usr/bin/env python
# coding: utf-8


# TODO test: commit --sub with dirty work dir
# TODO commit --sub add history to commit log
import imp
import os
import shutil
import unittest

gift = imp.load_source('gift', './gift')

cmdx = gift.cmdx
cmdout = gift.cmdout
cmd0 = gift.cmd0
read_file = gift.read_file
write_file = gift.write_file
pj = gift.pj
dd = gift.dd
_bytes = gift._bytes

Git = gift.Git


# root of this repo
this_base = os.path.dirname(__file__)

giftp = pj(this_base, "gift")
origit = "git"

emptyp = pj(this_base, "testdata", "empty")
superp = pj(this_base, "testdata", "super")
subbarp = pj(this_base, "testdata", "super", "foo", "bar")
subwowp = pj(this_base, "testdata", "super", "foo", "wow")
bargitp = pj(this_base, "testdata", "bargit")
barp = pj(this_base, "testdata", "bar")


def _clean_case():
    for d in ("empty", ):
        p = pj(this_base, "testdata",        d)
        cmdx(origit, "reset", "--hard",     cwd=p)
        cmdx(origit, "clean", "-dxf",        cwd=p)

    force_remove(pj(this_base, "testdata", "empty", ".git"))
    force_remove(pj(this_base, "testdata", "super", ".git"))
    force_remove(barp)
    cmdx(origit, "reset", "testdata", cwd=this_base)
    cmdx(origit, "checkout", "testdata", cwd=this_base)
    cmdx(origit, "clean", "-dxf", cwd=this_base)


class BaseTest(unittest.TestCase):

    def setUp(self):

        _clean_case()

        # .git can not be track in a git repo.
        # need to manually create it.
        write_file(pj(this_base, "testdata", "super", ".git"),
                   "gitdir: ../supergit")

    def tearDown(self):
        if os.environ.get("GIFT_NOCLEAN", None) == "1":
            return
        _clean_case()


class TestGit(BaseTest):

    def test_ref_get(self):
        g = Git(start_dir=superp)
        t = g.ref_get("abc")
        self.assertIsNone(t)

        t = g.ref_get("master")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

        t = g.ref_get("refs/heads/master")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

        t = g.ref_get("c3954c897dfe40a5b99b7145820eeb227210265c")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

    def test_remote_get(self):
        g = Git(start_dir=superp)
        t = g.remote_get("abc")
        self.assertIsNone(t)

        cmdx(origit, "remote", "add", "newremote", "newremote-url", cwd=superp)
        t = g.remote_get("newremote")
        self.assertEqual("newremote-url", t)

    def test_blob_new(self):
        write_file(pj(superp, "newblob"), "newblob!!!")
        g = Git(start_dir=superp)
        blobhash = g.blob_new("newblob")

        content = cmd0(origit, "cat-file", "-p", blobhash, cwd=superp)
        self.assertEqual("newblob!!!", content)

    def test_add_tree(self):

        g = Git(start_dir=superp)

        roottreeish = g.get_tree("HEAD")

        dd(cmdx(origit, "ls-tree", "87486e2d4543eb0dd99c1064cc87abdf399cde9f", cwd=superp))
        self.assertEqual("87486e2d4543eb0dd99c1064cc87abdf399cde9f", roottreeish)

        # shallow add

        newtree = g.tree_add_obj(roottreeish, "nested", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual([
            ".gift",
            "imsuperman",
            "nested/.gift",
            "nested/imsuperman",
        ], files)

        # add nested

        newtree = g.tree_add_obj(newtree, "a/b/c/d", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual([
            ".gift",
            "a/b/c/d/.gift",
            "a/b/c/d/imsuperman",
            "imsuperman",
            "nested/.gift",
            "nested/imsuperman",
        ], files)

        # replace nested

        newtree = g.tree_add_obj(newtree, "a/b/c", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual([
            ".gift",
            "a/b/c/.gift",
            "a/b/c/imsuperman",
            "imsuperman",
            "nested/.gift",
            "nested/imsuperman",
        ], files)

        # replace a blob with tree

        newtree = g.tree_add_obj(newtree, "a/b/c/imsuperman", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual([
            ".gift",
            "a/b/c/.gift",
            "a/b/c/imsuperman/.gift",
            "a/b/c/imsuperman/imsuperman",
            "imsuperman",
            "nested/.gift",
            "nested/imsuperman",
        ], files)

        # replace a blob in mid of path with tree

        newtree = g.tree_add_obj(newtree, "nested/imsuperman/b/c", roottreeish)

        files = cmdout(origit, "ls-tree", "-r", "--name-only", newtree, cwd=superp)
        self.assertEqual([
            ".gift",
            "a/b/c/.gift",
            "a/b/c/imsuperman/.gift",
            "a/b/c/imsuperman/imsuperman",
            "imsuperman",
            "nested/.gift",
            "nested/imsuperman/b/c/.gift",
            "nested/imsuperman/b/c/imsuperman",
        ], files)


class TestGift(BaseTest):

    def test_clone_sub(self):
        cmdx(giftp, "init", cwd=emptyp)
        a = cmdx(giftp, "clone", "--sub", "../bargit@master", "path/to/bar", cwd=emptyp)
        dd(a)
        self._gitoutput([giftp, "ls-files"], [
            ".gift",
            ".gift-refs",
            "path/to/bar/bar",
        ], cwd=emptyp)

        self._fcontent("dirs:\n  path/to/bar: ../bargit@master\n", emptyp, ".gift")
        self._fcontent("\n".join([
                "- - path/to/bar",
                "  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af",
                "", 
        ]), emptyp, ".gift-refs")
        self._fcontent("bar\n", emptyp, "path/to/bar/bar")


    def test_init_sub(self):
        self._nofile(subbarp, "bar")
        self._nofile(subwowp, "wow")

        for _ in range(2):
            cmdx(giftp, "init", "--sub", cwd=superp)

            self._fcontent("bar\n", subbarp, "bar")
            self._fcontent("wow\n", subwowp, "wow")

            self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subbarp)
            self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subwowp)
            self._gitoutput([giftp, "ls-files"], [".gift", "imsuperman"], cwd=superp)

    def test_commit_in_super(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
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

    def test_commit_sub(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        _, out, err = cmdx(giftp, "commit", "--sub", cwd=superp)
        dd(out)
        dd(err)

        self._gitoutput([giftp, "ls-files"],
                        [
            ".gift",
            ".gift-refs",
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
            superp, ".gift-refs",
        )

    def test_fetch_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)
        fetched_hash = cmd0(giftp, "rev-parse", "origin/master", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash)

    def test_merge_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, "commit", "--sub", cwd=superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)
        cmdx(giftp, "merge", "--sub", cwd=superp)
        fetched_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash, "HEAD is updated to latest master")

    def test_reset_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, "commit", "--sub", cwd=superp)

        ori_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)
        cmdx(giftp, "merge", "origin/master", cwd=subbarp)
        fetched_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash, "HEAD is updated to latest master")

        cmdx(giftp, "reset", "--sub", cwd=superp)
        reset_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        self.assertEqual(ori_hash, reset_hash, "HEAD is reset to original master")

    def _add_commit_to_bar_from_other_clone(self):
        cmdx(origit, "clone", bargitp, barp)

        write_file(pj(barp, "for_fetch"), "for_fetch")
        cmdx(origit, "add", "for_fetch", cwd=barp)
        cmdx(origit, "commit", "-m", "add for_fetch", cwd=barp)
        cmdx(origit, "push", "origin", "master", cwd=barp)

        headhash = cmd0(origit, "rev-parse", "HEAD", cwd=barp)
        return headhash

    def test_op_in_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        superhash = cmd0(origit, "rev-parse", "HEAD", cwd=superp)
        dd(superhash)

        gift_super_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=superp)
        self.assertEqual(superhash, gift_super_hash, "gift should get the right super HEAD hash")

        barhash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        self.assertNotEqual(barhash, superhash, "gift should get a different hash in sub dir bar")

        self._add_file_to_subbar()

        superhash2 = cmd0(origit, "rev-parse", "HEAD", cwd=superp)
        self.assertEqual(superhash, superhash2, "commit in sub dir should not change super dir HEAD")

    def test_populate_super_ref(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        # commit --sub should populate super/head
        cmdx(giftp, "commit", "--sub", cwd=superp)
        self._check_initial_superhead()

        self._add_file_to_subbar()
        self._remove_super_ref()

        # init --sub should populate super/head
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._check_initial_superhead()

    def test_populate_super_ref2(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        # commit --sub should populate super/head
        cmdx(giftp, "commit", "--sub", cwd=superp)
        self._check_initial_superhead()

        head_of_bar = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)

        state0 = read_file(pj(superp, ".gift-refs"))

        self._add_file_to_subbar()
        cmdx(giftp, "commit", "--sub", cwd=superp)

        head1 = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)
        self.assertNotEqual(head_of_bar, head1)

        state1 = read_file(pj(superp, ".gift-refs"))
        self.assertNotEqual(state0, state1)

        # changing HEAD in super repo should repopulate super/head ref in sub repo
        cmdx(giftp, "reset", "HEAD~", cwd=superp)
        head2 = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)
        self.assertNotEqual(head_of_bar, head2)

    def test_super_checkout_should_populate_super_ref(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, "commit", "--sub", cwd=superp)
        head_of_bar = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)

        self._add_file_to_subbar()
        cmdx(giftp, "commit", "--sub", cwd=superp)
        head_of_bar1 = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)

        self.assertNotEqual(head_of_bar, head_of_bar1)

        # changing HEAD in super repo should repopulate super/head ref in sub repo
        cmdx(giftp, "checkout", "HEAD~", cwd=superp)
        head_of_bar_after_checkout = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)

        self.assertNotEqual(head_of_bar, head_of_bar_after_checkout)

    def _remove_super_ref(self):
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subbarp)
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subwowp)

    def _check_initial_superhead(self):
        _, out, _ = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", out[0])

        _, out, _ = cmdx(giftp, "rev-parse", "refs/remotes/super/head", cwd=subwowp)
        self.assertEqual("6bf37e52cbafcf55ff4710bb2b63309b55bf8e54", out[0])

    def _add_file_to_subbar(self):
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
        shutil.rmtree(fn)
    except BaseException:
        pass

    try:
        os.unlink(fn)
    except BaseException:
        pass
