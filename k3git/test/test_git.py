import os
import unittest
import shutil

import k3ut
from k3git import GitOpt
from k3git import Git


from k3fs import fread
from k3fs import fwrite

from k3handy.cmd import cmd0
from k3handy.cmd import cmdf
from k3handy.cmd import cmdx
from k3handy.cmd import cmdout
from k3handy import CalledProcessError


from k3handy.path import pjoin

dd = k3ut.dd

this_base = os.path.dirname(__file__)

origit = "git"

superp = pjoin(this_base, "testdata", "super")
supergitp = pjoin(this_base, "testdata", "supergit")
wowgitp = pjoin(this_base, "testdata", "wowgit")


class BaseTest(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None

        _clean_case()

        # .git can not be track in a git repo.
        # need to manually create it.
        fwrite(pjoin(this_base, "testdata", "super", ".git"),
               "gitdir: ../supergit")

    def tearDown(self):
        if os.environ.get("GIFT_NOCLEAN", None) == "1":
            return
        _clean_case()

    def _fcontent(self, txt, *ps):
        self.assertTrue(os.path.isfile(pjoin(*ps)), pjoin(*ps) + " should exist")

        actual = fread(pjoin(*ps))
        self.assertEqual(txt, actual, "check file content")


class TestGitInit(BaseTest):

    def test_init(self):
        g = Git(GitOpt(), gitdir=supergitp, working_dir=superp)
        g.checkout('master')
        self._fcontent("superman\n", superp, "imsuperman")

        self.assertRaises(CalledProcessError,
                          g.checkout, "foo")


class TestGitHighlevel(BaseTest):

    def test_checkout(self):
        g = Git(GitOpt(), cwd=superp)
        g.checkout('master')
        self._fcontent("superman\n", superp, "imsuperman")

        self.assertRaises(CalledProcessError,
                          g.checkout, "foo")

    def test_fetch(self):
        g = Git(GitOpt(), cwd=superp)

        g.fetch(wowgitp)
        hsh = g.cmdf('log', '-n1', '--format=%H', 'FETCH_HEAD', flag='0')

        self.assertEqual('6bf37e52cbafcf55ff4710bb2b63309b55bf8e54', hsh)


class TestGitRev(BaseTest):

    def test_rev_of(self):
        g = Git(GitOpt(), cwd=superp)
        t = g.rev_of("abc")
        self.assertIsNone(t)

        t = g.rev_of("master")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

        t = g.rev_of("refs/heads/master")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)

        t = g.rev_of("c3954c897dfe40a5b99b7145820eeb227210265c")
        self.assertEqual("c3954c897dfe40a5b99b7145820eeb227210265c", t)


class TestGitRemote(BaseTest):

    def test_remote_get(self):
        # TODO
        g = Git(GitOpt(), cwd=superp)
        t = g.remote_get("abc")
        self.assertIsNone(t)

        cmdx(origit, "remote", "add", "newremote", "newremote-url", cwd=superp)
        t = g.remote_get("newremote")
        self.assertEqual("newremote-url", t)

    def test_remote_add(self):
        # TODO
        g = Git(GitOpt(), cwd=superp)
        t = g.remote_get("abc")
        self.assertIsNone(t)

        g.remote_add("newremote", "newremote-url")
        t = g.remote_get("newremote")
        self.assertEqual("newremote-url", t)


class TestGitBlob(BaseTest):

    def test_blob_new(self):
        fwrite(pjoin(superp, "newblob"), "newblob!!!")
        # TODO
        g = Git(GitOpt(), cwd=superp)
        blobhash = g.blob_new("newblob")

        content = cmd0(origit, "cat-file", "-p", blobhash, cwd=superp)
        self.assertEqual("newblob!!!", content)


class TestGitTree(BaseTest):

    def test_tree_items(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of('master')

        lines = g.tree_items(tree)
        self.assertEqual([
            '100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\t.gift',
            '100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2\timsuperman'
        ], lines)

        lines = g.tree_items(tree, with_size=True)
        self.assertEqual([
            '100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c     163\t.gift',
            '100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2       9\timsuperman'
        ], lines)

        lines = g.tree_items(tree, name_only=True)
        self.assertEqual([
            '.gift',
            'imsuperman'
        ], lines)

        lines = g.tree_items(tree, name_only=True, with_size=True)
        self.assertEqual([
            '.gift',
            'imsuperman'
        ], lines)

    def test_parse_tree_item(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of('master')
        lines = g.tree_items(tree, with_size=True)

        got = g.parse_tree_item(lines[0])
        self.assertEqual({
            'fn': '.gift',
            'mode': '100644',
            'object': '15d2fff1101916d7212371fea0f3a82bda750f6c',
            'type': 'blob',
            'size': '163',
        }, got)

    def test_tree_new(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of('master')
        lines = g.tree_items(tree)

        itm = g.parse_tree_item(lines[0])
        obj = itm['object']

        treeish = g.tree_new(lines, 'foo', obj, mode='100755')
        got = g.tree_items(treeish)

        self.assertEqual([
            '100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\t.gift',
            '100755 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\tfoo',
            '100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2\timsuperman',
        ], got)

    def test_add_tree(self):

        # TODO opt
        g = Git(GitOpt(), cwd=superp)

        roottreeish = g.tree_of("HEAD")

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


class TestGitTreeItem(BaseTest):

    def test_treeitem_new(self):
        g = Git(GitOpt(), cwd=superp)

        tree = g.tree_of('master')
        lines = g.tree_items(tree, with_size=True)
        itm = g.parse_tree_item(lines[0])
        obj = itm['object']

        got = g.treeitem_new("foo", obj)
        self.assertEqual('100644 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\tfoo', got)

        got = g.treeitem_new("foo", obj, mode='100755')
        self.assertEqual('100755 blob 15d2fff1101916d7212371fea0f3a82bda750f6c\tfoo', got)


class TestGitOut(BaseTest):

    def test_out(self):
        script = r'''import k3git; k3git.Git(k3git.GitOpt(), ctxmsg="foo").out(1, "bar", "wow")'''

        got = cmdf('python', '-c', script, flag='x0')
        self.assertEqual('foo: bar wow', got)


def _clean_case():

    force_remove(pjoin(this_base, "testdata", "super", ".git"))
    cmdx(origit, "reset", "testdata", cwd=this_base)
    cmdx(origit, "checkout", "testdata", cwd=this_base)
    cmdx(origit, "clean", "-dxf", cwd=this_base)


def force_remove(fn):

    try:
        shutil.rmtree(fn)
    except BaseException:
        pass

    try:
        os.unlink(fn)
    except BaseException:
        pass
