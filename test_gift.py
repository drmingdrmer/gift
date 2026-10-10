#!/usr/bin/env python
# coding: utf-8


# TODO test: commit --sub with dirty work dir
# TODO commit --sub add history to commit log
import importlib.machinery
import importlib.util
import os
import shutil
import tempfile
import unittest

from k3fs import fread
from k3fs import fwrite
from k3git import GitOpt
from k3handy import cmd0
from k3handy import cmdf
from k3handy import cmdout
from k3handy import cmdtty
from k3handy import cmdx
from k3handy import dd
from k3handy import pjoin

loader = importlib.machinery.SourceFileLoader('gift', './gift')
spec = importlib.util.spec_from_loader('gift', loader)
gift = importlib.util.module_from_spec(spec)
loader.exec_module(gift)

CalledProcessError = gift.CalledProcessError

Git = gift.Git
Gift = gift.Gift


# root of this repo
this_base = os.path.dirname(__file__)

giftp = pjoin(this_base, "gift")
subrepop = pjoin(this_base, "git-subrepo")
origit = "git"

emptyp = pjoin(this_base, "testdata", "empty")
superp = pjoin(this_base, "testdata", "super")
supergitp = pjoin(this_base, "testdata", "supergit")
subbarp = pjoin(this_base, "testdata", "super", "foo", "bar")
subwowp = pjoin(this_base, "testdata", "super", "foo", "wow")
bargitp = pjoin(this_base, "testdata", "bargit")
barp = pjoin(this_base, "testdata", "bar")

execpath = cmd0(origit, '--exec-path')

ident_args = [
        '-c', 'user.name=fooUser',
        '-c', 'user.email=my@email.org',
]

def _clean_case():
    for d in ("empty", ):
        p = pjoin(this_base, "testdata", d)
        if os.path.exists(pjoin(p, ".git")):
            cmdx(origit, "reset", "--hard", cwd=p)
            cmdx(origit, "clean", "-dxf", cwd=p)

    force_remove(pjoin(this_base, "testdata", "empty", "bar"))
    force_remove(pjoin(this_base, "testdata", "empty", ".git"))
    force_remove(pjoin(this_base, "testdata", "super", ".git"))
    force_remove(barp)
    cmdx(origit, "reset", "testdata", cwd=this_base)
    cmdx(origit, "checkout", "testdata", cwd=this_base)
    cmdx(origit, "clean", "-dxf", "testdata", cwd=this_base)


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

    def _remove_super_ref(self):
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subbarp)
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subwowp)

    def _check_initial_superhead(self):
        _, out, _ = cmdx(giftp, "rev-parse",
                         "refs/remotes/super/head", cwd=subbarp)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", out[0])

        _, out, _ = cmdx(giftp, "rev-parse",
                         "refs/remotes/super/head", cwd=subwowp)
        self.assertEqual("6bf37e52cbafcf55ff4710bb2b63309b55bf8e54", out[0])

    def _add_file_to_subbar(self):
        fwrite(pjoin(subbarp, "newbar"), "newbar")
        cmdx(giftp, "add", "newbar", cwd=subbarp)
        cmdx(giftp, *ident_args, "commit", "-m", "add newbar", cwd=subbarp)

        # TODO test no .gift file

    def _git_trace(self, *cmds, cwd):
        # The git commands that one gift command runs
        with tempfile.TemporaryDirectory() as tmpdir:
            tracep = pjoin(tmpdir, "trace")
            cmdx(giftp, *cmds, cwd=cwd, env={"GIT_TRACE": tracep})
            lines = fread(tracep).splitlines()

        traced = []
        for line in lines:
            if "trace: built-in: " in line:
                traced.append(line.split("trace: built-in: ", 1)[1])
        return traced

    def _gitoutput(self, cmds, lines, **kwargs):
        _, out, _ = cmdx(*cmds, **kwargs)
        self.assertEqual(lines, out)

    def _nofile(self, *ps):
        self.assertFalse(os.path.isfile(pjoin(*ps)),
                         "no file in " + pjoin(*ps))

    def _fcontent(self, txt, *ps):
        self.assertTrue(os.path.isfile(pjoin(*ps)),
                        pjoin(*ps) + " should exist")

        actual = fread(pjoin(*ps))
        self.assertEqual(txt, actual, "check file content")


class TestGiftAPI(BaseTest):

    def test_get_subrepo_config(self):
        gg = Gift(GitOpt().update({
            'startpath': [superp],
            'git_dir': None,
            'work_tree': None,
        }))
        gg.init_git_config()

        rel, sb = gg.get_subrepo_config(pjoin(superp, "f"))
        self.assertEqual(('', None), (rel, sb), "inexistent path")

        rel, sb = gg.get_subrepo_config(pjoin(superp, "foo"))
        self.assertEqual(('', None), (rel, sb), "inexistent path foo")

        rel, sb = gg.get_subrepo_config(pjoin(superp, "foo/bar"))
        self.assertEqual('foo/bar', rel)
        self.assertEqual({
            'bareenv': {'GIT_DIR': this_base + '/testdata/supergit/gift/subdir/foo/bar'},
            'dir': 'foo/bar',
            'env': {'GIT_DIR': this_base + '/testdata/supergit/gift/subdir/foo/bar',
                    'GIT_WORK_TREE': this_base + '/testdata/super/foo/bar'},
            'refhead': 'refs/gift/sub/foo%2Fbar',
            'sub_gitdir': 'gift/subdir/foo/bar',
            'upstream': {'branch': 'master', 'name': 'origin', 'url': this_base + '/testdata/bargit'}
        }, sb)

    def test_parse_remote(self):
        gg = Gift(GitOpt().update({
            'startpath': [superp],
            'git_dir': None,
            'work_tree': None,
        }))

        # The "@" of a user name is not the one before the branch
        ups = gg.parse_remote("wiki", "ssh://git@github.com/a/b.wiki.git@master")
        self.assertEqual(["origin", "ssh://git@github.com/a/b.wiki.git", "master"], ups)

    def test_is_relative_path(self):
        # Whether git reads the url as a path relative to its cwd
        cases = {
            "up.git": True,
            "./up.git": True,
            "../up.git": True,
            "dir/a:b.git": True,
            "": False,
            "/abs/up.git": False,
            "~/up.git": False,
            "~user/up.git": False,
            "host:up.git": False,
            "git@host:dir/up.git": False,
            "https://host/dir/up.git": False,
            "file:///abs/up.git": False,
        }
        got = {url: gift.is_relative_path(url) for url in cases}
        self.assertEqual(cases, got)

    def test_join_opt_values(self):
        # The args of the command, after "log", stay as they are
        args = ["-C", "d", "--git-dir", "g", "-c", "a=b", "--work-tree", "w", "--namespace", "n",
                "--super-prefix", "s", "-p", "log", "--git-dir", "x"]
        want = ["-C", "d", "--git-dir=g", "-c", "a=b", "--work-tree=w", "--namespace=n",
                "--super-prefix=s", "-p", "log", "--git-dir", "x"]
        self.assertEqual(want, gift.join_opt_values(args))

        # Without a value, git reports the option
        self.assertEqual(["--git-dir"], gift.join_opt_values(["--git-dir"]))

    def test_is_outside(self):
        cases = {
            "..": True,
            "../x": True,
            "../..": True,
            "..dep": False,
            "..dep/x": False,
            ".": False,
            "x": False,
        }
        got = {relpath: gift.is_outside(relpath) for relpath in cases}
        self.assertEqual(cases, got)


class TestGiftPartialInit(BaseTest):

    def setUp(self):
        super(TestGiftPartialInit, self).setUp()

        gg = Gift(GitOpt().update({
            'startpath': [superp],
            'git_dir': None,
            'work_tree': None,

        }))
        gg.init_git_config()

        rel, sb = gg.get_subrepo_config(pjoin(superp, "foo/bar"))
        self.gg = gg
        self.sb = sb
        self.rel = rel

    def test_init_1_with_inited(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])

        cmdx(giftp, "init", "--sub", cwd=superp)
        self._fcontent("bar\n", subbarp, "bar")

    def test_init_2_with_remote(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])
        cmdx(origit, "remote", "add", self.sb['upstream']['name'],
             self.sb['upstream']['url'], env=self.sb['bareenv'])

        cmdx(giftp, "init", "--sub", cwd=superp)
        self._fcontent("bar\n", subbarp, "bar")

    def test_init_3_with_fetched(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])
        cmdx(origit, "remote", "add", self.sb['upstream']['name'],
             self.sb['upstream']['url'], env=self.sb['bareenv'])
        cmdx(origit, "fetch", self.sb['upstream']
             ['name'], env=self.sb['bareenv'], cwd=superp)

        cmdx(giftp, "init", "--sub", cwd=superp)
        self._fcontent("bar\n", subbarp, "bar")

    def test_init_4_already_checkout(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])
        cmdx(origit, "remote", "add", self.sb['upstream']['name'],
             self.sb['upstream']['url'], env=self.sb['bareenv'])
        cmdx(origit, "fetch", self.sb['upstream']
             ['name'], env=self.sb['bareenv'], cwd=superp)

        os.makedirs(self.sb['env']['GIT_WORK_TREE'], mode=0o755)
        cmdx(origit, "checkout",
             self.sb['upstream']['branch'], env=self.sb['env'])
        self._fcontent("bar\n", subbarp, "bar")

        os.unlink(pjoin(subbarp, "bar"))

        # init --sub should not checkout again to modify work tree
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._nofile(subbarp, "bar")


class TestGiftDelegate(BaseTest):

    def test_opt_version(self):
        out = cmdout(giftp, "--version", cwd=superp)
        self.assertEqual('gift version 0.2.0', out[0])
        self.assertEqual(2, len(out))

    def test_opt_help(self):
        out = cmdout(giftp, "--help", cwd=superp)
        self.assertIn(
            'These are common Git commands used in various situations:', out)
        self.assertIn('Gift extended command:', out)
        self.assertIn('gift clone --sub <url>@<branch> <dir>', out)

    def test_opt_paging(self):
        out = cmdout(giftp, "gift-debug", cwd=superp)
        self.assertIn('paging: null', '\n'.join(out))

        out = cmdout(giftp, '-p', "gift-debug", cwd=superp)
        self.assertIn('paging: true', '\n'.join(out))

        out = cmdout(giftp, '--paginate', "gift-debug", cwd=superp)
        self.assertIn('paging: true', '\n'.join(out))

        out = cmdout(giftp, '--no-pager', "gift-debug", cwd=superp)
        self.assertIn('paging: false', '\n'.join(out))

    def test_opt_manual_paths(self):
        man_path = cmd0(origit, '--man-path')
        info_path = cmd0(origit, '--info-path')
        html_path = cmd0(origit, '--html-path')

        self.assertEqual(man_path, cmd0(giftp, '--man-path'))
        self.assertEqual(info_path, cmd0(giftp, '--info-path'))
        self.assertEqual(html_path, cmd0(giftp, '--html-path'))

    def test_opt_exec_path(self):
        rst = cmd0(giftp, "--exec-path")
        self.assertEqual(execpath, rst)

        rst = cmd0(giftp, "--exec-path", "--exec-path=" + execpath)
        self.assertEqual(execpath, rst)

        rst = cmd0(giftp, "--exec-path=" + execpath, "--exec-path")
        self.assertEqual(execpath, rst)

        out = cmdout(giftp, "--exec-path=/foo/",
                     "-p", "gift-debug", cwd=superp)
        self.assertEqual([

            'gift-debug',
            'additional: {}',
            'informative_cmds: {}',
            'opt:',
            '  bare: false',
            '  confkv: []',
            '  exec_path: /foo/',
            '  git_dir: null',
            '  namespace: null',
            '  no_replace_objects: false',
            '  paging: true',
            '  startpath: []',
            '  super_prefix: null',
            '  work_tree: null',
            '',
            'evaluated cwd: ' + this_base + '/testdata/super',
            'evaluated git_dir: None',
            'evaluated working_dir: None',
        ], out)

    def test_opt_minus_c(self):
        code, out, err = cmdtty(
            giftp, "-c", "pager.log=head -n 1", "log", "--no-color", cwd=superp)
        self.assertEqual(0, code)
        self.assertEqual([
            'commit c3954c897dfe40a5b99b7145820eeb227210265c (HEAD -> master)'
        ], out)
        self.assertEqual([], err)

    def test_opt_git_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = cmdout(giftp, '--git-dir=' + supergitp,
                         "log", "-n1", cwd=tmpdir)

        self.assertEqual([
            'commit c3954c897dfe40a5b99b7145820eeb227210265c',
            'Author: drdr xp <drdr.xp@gmail.com>',
            'Date:   Fri Jan 24 15:01:01 2020 +0800',
            '',
            '    add super'], out)

    def test_opt_worktree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = cmdout(giftp,
                         '--git-dir=' + supergitp,
                         '--work-tree=' + tmpdir,
                         "log", "-n1", cwd=".")

        self.assertEqual([
            'commit c3954c897dfe40a5b99b7145820eeb227210265c',
            'Author: drdr xp <drdr.xp@gmail.com>',
            'Date:   Fri Jan 24 15:01:01 2020 +0800',
            '',
            '    add super'], out)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = cmdout(giftp,
                         '--git-dir=' + supergitp,
                         '--work-tree=' + tmpdir,
                         "diff",
                         "--name-only",
                         "--relative",
                         "HEAD",
                         cwd=".")

        self.assertEqual(['.gift', 'imsuperman'], out)

    def test_opt_big_c(self):

        with tempfile.TemporaryDirectory() as tmpdir:
            out = cmdout(giftp,
                         '-C', this_base,
                         '--git-dir=' + pjoin('testdata', 'supergit'),
                         '--work-tree=' + pjoin("testdata", 'super'),
                         "ls-files",
                         cwd=tmpdir)

        self.assertEqual(['.gift', 'imsuperman'], out)

        out = cmdout(giftp, '-C', pjoin('testdata', 'super'),
                     "log", "-1", "--format=%s", cwd=this_base)
        self.assertEqual(['add super'], out)

    def test_opt_big_c_sub_gitdir(self):
        # emptyp/.git is a dir, so `git rev-parse --git-dir` prints ".git"
        cmdx(giftp, "init", cwd=emptyp)

        with tempfile.TemporaryDirectory() as tmpdir:
            cmdx(giftp, *ident_args, '-C', emptyp, "clone", "--sub",
                 "../bargit@master", "bar", cwd=tmpdir)
            self.assertFalse(os.path.exists(pjoin(tmpdir, ".git")))

        self.assertTrue(os.path.isdir(pjoin(emptyp, ".git", "gift", "subdir", "bar")))

    def test_opt_big_c_init(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.mkdir(pjoin(tmpdir, "newrepo"))
            cmdx(giftp, '-C', "newrepo", "init", cwd=tmpdir)

            self.assertFalse(os.path.exists(pjoin(tmpdir, ".git")))
            self.assertTrue(os.path.isdir(pjoin(tmpdir, "newrepo", ".git")))

    def test_opt_big_c_missing_dir(self):
        missing = pjoin(superp, "nosuchdir")
        want = ["fatal: cannot change to '" + missing + "': No such file or directory"]

        # A git command, an informative command, and no command
        for cmds in (["status"], ["--version"], []):
            e = None
            try:
                cmdx(giftp, '-C', "nosuchdir", *cmds, cwd=superp)
            except CalledProcessError as ee:
                e = ee

            self.assertEqual(128, e.returncode, cmds)
            self.assertEqual([], e.out, cmds)
            self.assertEqual(want, e.err, cmds)

    def test_env_git_dir(self):
        out = cmdout(giftp, "log", "-1", "--format=%s",
                     cwd=this_base, env={"GIT_DIR": bargitp})
        self.assertEqual(['add bar'], out)

    def test_error_output(self):
        e = None
        try:
            cmdx(giftp, "abc")
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(1, e.returncode)
        self.assertEqual([], e.out)
        self.assertEqual(
            "git: 'abc' is not a git command. See 'git --help'.", e.err[0])

        # there should not raw python error returned
        self.assertNotIn('Traceback', "".join(e.out))
        self.assertNotIn('Traceback', "".join(e.err))

    def test_no_cmd(self):
        e = None
        try:
            cmdx(giftp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(1, e.returncode)
        self.assertIn("usage: git", e.out[0], "stderr output git help")
        self.assertIn('Gift extended command:', e.out, "help with gift info")
        self.assertEqual([], e.err)

        # there should not raw python error returned
        self.assertNotIn('Traceback', "".join(e.out))
        self.assertNotIn('Traceback', "".join(e.err))

    def test_cmd_tty(self):
        # TODO this test does not belongs to gift
        code, out, err = cmdtty(
            origit, "log", "-n1", "c3954c897dfe40a5b99b7145820eeb227210265c", cwd=superp)

        self.assertEqual(0, code)
        # on ci: the output lack of: '\x1b[?1h\x1b=\r'
        # self.assertEqual([
        #         '\x1b[?1h\x1b=\r\x1b[33mcommit c3954c897dfe40a5b99b7145820eeb227210265c\x1b[m\x1b[33m (\x1b[m\x1b[1;36mHEAD -> \x1b[m\x1b[1;32mmaster\x1b[m\x1b[33m)\x1b[m\x1b[m\r',
        #         'Author: drdr xp <drdr.xp@gmail.com>\x1b[m\r',
        #         'Date:   Fri Jan 24 15:01:01 2020 +0800\x1b[m\r',
        #         '\x1b[m\r',
        #         '    add super\x1b[m\r',
        #         '\r\x1b[K\x1b[?1l\x1b>'
        # ], out, "pseudo tty cheat git to output colored output")
        o = ''.join(out)
        self.assertIn("\x1b[33", o)
        self.assertIn("commit c3954c897dfe40a5b99b7145820eeb227210265c", o)
        self.assertIn("drdr xp", o)
        self.assertEqual([
        ], err)

    def test_interactive_mode(self):
        _, out, err = cmdtty(
            giftp, "log", "-n1", "c3954c897dfe40a5b99b7145820eeb227210265c", cwd=superp)

        # self.assertEqual([
        #         '\x1b[?1h\x1b=\r\x1b[33mcommit c3954c897dfe40a5b99b7145820eeb227210265c\x1b[m\x1b[33m (\x1b[m\x1b[1;36mHEAD -> \x1b[m\x1b[1;32mmaster\x1b[m\x1b[33m)\x1b[m\x1b[m\r',
        #         'Author: drdr xp <drdr.xp@gmail.com>\x1b[m\r',
        #         'Date:   Fri Jan 24 15:01:01 2020 +0800\x1b[m\r',
        #         '\x1b[m\r',
        #         '    add super\x1b[m\r',
        #         '\r\x1b[K\x1b[?1l\x1b>'
        # ], out, "delegated git command should output color")
        o = ''.join(out)
        self.assertIn("\x1b[33", o)
        self.assertIn("commit c3954c897dfe40a5b99b7145820eeb227210265c", o)
        self.assertIn("drdr xp", o)

        self.assertEqual([], err)


class TestGift(BaseTest):
    def test_in_git_dir(self):

        cmdx(giftp, "log", "-n1", cwd=supergitp)

        try:
            cmdx(giftp, "commit", "--sub", cwd=supergitp)
        except CalledProcessError as e:
            self.assertEqual(2, e.returncode)
            self.assertEqual([], e.out)
            self.assertEqual(
                ["--sub can not be used in git-dir:" + supergitp], e.err)

        try:
            cmdx(giftp, "status", cwd=supergitp)
        except CalledProcessError as e:
            self.assertEqual(128, e.returncode)
            self.assertEqual([], e.out)
            self.assertEqual([
                'fatal: this operation must be run in a work tree'
            ], e.err)

    # def test_no_gift_file(self):
    #     workdir = emptyp
    #     cmdx(giftp, "init", cwd=workdir)

    #     # TODO
    #     try:
    #         cmdx(giftp, "commit", "--sub", cwd=workdir)
    #     except CalledProcessError as e:
    #         self.assertEqual(2, e.returncode)
    #         self.assertEqual([], e.out)
    #         self.assertEqual([
    #                 "No .gift found in:" + workdir,
    #                 "To add sub repo:",
    #                 "    git clone --sub <url> <path>",
    #         ], e.err)

    def test_clone_not_in_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmdx(giftp, "clone", bargitp, "bar", cwd=tmpdir)
            self._gitoutput([giftp, "ls-files"], [
                "bar"
            ], cwd=pjoin(tmpdir, 'bar'))

            self._fcontent("bar\n", tmpdir, "bar/bar")

    def test_clone_in_other_repo(self):
        cmdx(giftp, "init", cwd=emptyp)
        cmdx(giftp, "clone", "../bargit", "bar", cwd=emptyp)
        self._gitoutput([giftp, "ls-files"], [
            "bar"
        ], cwd=pjoin(emptyp, "bar"))

        self._fcontent("bar\n", emptyp, "bar/bar")

    def test_clone_sub(self):
        cmdx(giftp, "init", cwd=emptyp)
        code, out, err = cmdx(giftp, *ident_args,  "clone", "--sub",
                              "../bargit@master", "path/to/bar", cwd=emptyp)
        for l in (
                'GIFT: path/to/bar: add remote: origin ' + bargitp,
                'GIFT: path/to/bar: fetch origin ' + bargitp,
                "From " + bargitp,
        ):
            self.assertIn(l, "\n".join(err),
                          "it should output fetching status")

        self._gitoutput([giftp, "ls-files"], [
            ".gift",
            ".gift-refs",
            "path/to/bar/bar",
        ], cwd=emptyp)

        self._fcontent(
            "dirs:\n  path/to/bar: ../bargit@master\n", emptyp, ".gift")
        self._fcontent("\n".join([
            "- - path/to/bar",
            "  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af",
            "",
        ]), emptyp, ".gift-refs")
        self._fcontent("bar\n", emptyp, "path/to/bar/bar")

    def test_clone_sub_failed(self):
        cmdx(giftp, "init", cwd=emptyp)
        confp = pjoin(emptyp, ".gift")
        bad_gitdir = pjoin(emptyp, ".git", "gift", "subdir", "bad")

        # A bad url, before any .gift exists
        e = None
        try:
            cmdx(giftp, *ident_args, "clone", "--sub", "../nosuch@master", "bad", cwd=emptyp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(128, e.returncode)
        self.assertFalse(os.path.exists(confp))
        self.assertEqual([], cmdout(origit, "rev-list", "--all", cwd=emptyp))
        self.assertFalse(os.path.exists(bad_gitdir))

        # A bad branch, with .gift from an earlier clone --sub
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "bar", cwd=emptyp)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=emptyp)

        e = None
        try:
            cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@nosuch", "bad", cwd=emptyp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(1, e.returncode)
        self._fcontent("dirs:\n  bar: ../bargit@master\n", confp)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=emptyp))
        self.assertFalse(os.path.exists(bad_gitdir))

        # A dir that is already a sub-repo
        e = None
        try:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "bar", cwd=emptyp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(2, e.returncode)
        self.assertEqual(["clone --sub: bar is already a sub-repo in .gift"], e.err)
        self._fcontent("dirs:\n  bar: ../bargit@master\n", confp)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=emptyp))

        cmdx(giftp, "init", "--sub", cwd=emptyp)

    def test_clone_sub_failed_commit(self):
        cmdx(giftp, "init", cwd=emptyp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "bar", cwd=emptyp)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=emptyp)
        index = cmdout(origit, "ls-files", "--stage", ".gift", ".gift-refs", cwd=emptyp)

        hookp = pjoin(emptyp, ".git", "hooks", "pre-commit")
        fwrite(hookp, "#!/bin/sh\nexit 1\n")
        os.chmod(hookp, 0o755)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "wow", cwd=emptyp)

        self.assertEqual(1, failure.exception.returncode)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=emptyp))
        self.assertEqual(index, cmdout(origit, "ls-files", "--stage", ".gift", ".gift-refs", cwd=emptyp))
        self._fcontent("dirs:\n  bar: ../bargit@master\n", emptyp, ".gift")
        self._fcontent("- - bar\n  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af\n", emptyp, ".gift-refs")
        self.assertFalse(os.path.exists(pjoin(emptyp, "wow")))
        self.assertFalse(os.path.exists(pjoin(emptyp, ".git", "gift", "subdir", "wow")))

        # Without the hook, the same clone works
        os.unlink(hookp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "wow", cwd=emptyp)

        self._fcontent("dirs:\n  bar: ../bargit@master\n  wow: ../wowgit@master\n", emptyp, ".gift")
        self._fcontent("wow\n", emptyp, "wow", "wow")

    def test_clone_sub_dropped_dir(self):
        cmdx(giftp, "init", cwd=emptyp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "bar", cwd=emptyp)

        # Dropped from .gift, bar keeps its sub git dir, with the HEAD of bargit
        fwrite(pjoin(emptyp, ".gift"), "dirs: {}\n")
        cmdx(origit, *ident_args, "commit", "-m", "drop bar", ".gift", cwd=emptyp)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=emptyp)

        e = None
        try:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "bar", cwd=emptyp)
        except CalledProcessError as ee:
            e = ee

        bar_gitdir = pjoin(emptyp, ".git", "gift", "subdir", "bar")
        self.assertEqual(2, e.returncode)
        self.assertEqual(["clone --sub: an old sub-repo in bar left its git dir: " + bar_gitdir], e.err)
        self._fcontent("dirs: {}\n", emptyp, ".gift")
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=emptyp))

        bar_url = cmd0(origit, "--git-dir", bar_gitdir, "remote", "get-url", "origin")
        self.assertEqual(bargitp, bar_url)

        # Without the old sub git dir, .gift-refs still records the bargit
        # commit for bar. A failed clone keeps that entry.
        force_remove(bar_gitdir)

        e = None
        try:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@nosuch", "bar", cwd=emptyp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(1, e.returncode)
        self._fcontent("- - bar\n  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af\n", emptyp, ".gift-refs")

        # The clone checks out wowgit, and the commit that adds bar to .gift
        # drops the old entry
        cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "bar", cwd=emptyp)
        added_refs = cmdout(origit, "show", "HEAD~:.gift-refs", cwd=emptyp)

        self._fcontent("wow\n", emptyp, "bar", "wow")
        self._fcontent("- - bar\n  - 6bf37e52cbafcf55ff4710bb2b63309b55bf8e54\n", emptyp, ".gift-refs")
        self.assertEqual(["[]"], added_refs)

    def test_clone_sub_in_dropped_dir(self):
        cmdx(giftp, "init", cwd=emptyp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "dep", cwd=emptyp)

        # Dropped from .gift, dep keeps its ref in the super repo
        fwrite(pjoin(emptyp, ".gift"), "dirs: {}\n")
        cmdx(origit, *ident_args, "commit", "-m", "drop dep", ".gift", cwd=emptyp)

        cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "dep/child", cwd=emptyp)
        tree = cmdout(origit, "ls-tree", "-r", "--name-only", "HEAD", cwd=emptyp)

        self._fcontent("dirs:\n  dep/child: ../wowgit@master\n", emptyp, ".gift")
        self._fcontent("- - dep/child\n  - 6bf37e52cbafcf55ff4710bb2b63309b55bf8e54\n", emptyp, ".gift-refs")
        self.assertEqual([".gift", ".gift-refs", "dep/bar", "dep/child/wow"], tree)
        self.assertEqual(["wow"], cmdout(origit, "show", "HEAD:dep/child/wow", cwd=emptyp))

    def test_clone_sub_in_sub_dir(self):
        cmdx(giftp, "init", cwd=emptyp)
        cmdx(origit, "clone", "--bare", bargitp, pjoin(emptyp, "up.git"))
        dir1 = pjoin(emptyp, "dir1")
        os.mkdir(dir1)
        cmdx(origit, "clone", "--bare", bargitp, pjoin(dir1, "here.git"))

        # As git clone does, <dir> and a relative <url> are read from the cwd
        cmdx(giftp, *ident_args, "clone", "--sub", "../../bargit@master", "bar", cwd=dir1)
        cmdx(giftp, *ident_args, "clone", "--sub", "../up.git@master", "up", cwd=dir1)
        cmdx(giftp, *ident_args, "clone", "--sub", "here.git@master", "here", cwd=dir1)

        self._fcontent("dirs:\n  dir1/bar: ../bargit@master\n  dir1/here: ./dir1/here.git@master\n"
                       "  dir1/up: ./up.git@master\n", emptyp, ".gift")
        self._fcontent("bar\n", dir1, "bar", "bar")
        self._fcontent("bar\n", dir1, "up", "bar")
        self._fcontent("bar\n", dir1, "here", "bar")

    def test_init_sub(self):
        self._nofile(subbarp, "bar")
        self._nofile(subwowp, "wow")

        for _ in range(2):
            cmdx(giftp, "init", "--sub", cwd=superp)

            self._fcontent("bar\n", subbarp, "bar")
            self._fcontent("wow\n", subwowp, "wow")

            self._gitoutput([giftp, "symbolic-ref", "--short",
                             "HEAD"], ["master"], cwd=subbarp)
            self._gitoutput([giftp, "symbolic-ref", "--short",
                             "HEAD"], ["master"], cwd=subwowp)
            self._gitoutput([giftp, "ls-files"],
                            [".gift", "imsuperman"], cwd=superp)

    def test_init_sub_with_git_env(self):
        env = {"GIT_DIR": supergitp, "GIT_WORK_TREE": superp}
        cmdx(giftp, "init", "--sub", cwd=superp, env=env)

        self._fcontent("bar\n", subbarp, "bar")
        self._fcontent("wow\n", subwowp, "wow")

    def test_init_sub_with_files_from_super(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self._add_commit_to_bar_from_other_clone()

        # A fresh clone of super has the files of bar, but no git dir for bar
        force_remove(pjoin(supergitp, "gift", "subdir", "foo", "bar"))

        # It should adopt the commit in .gift-refs and keep the files
        cmdx(giftp, "init", "--sub", cwd=superp)

        bar_head = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", bar_head)

        self._gitoutput([giftp, "status", "--porcelain"], [], cwd=subbarp)
        self._gitoutput([giftp, "rev-parse", "--abbrev-ref", "@{upstream}"],
                        ["origin/master"], cwd=subbarp)

    def test_commit_in_super(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, "add", "foo", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "-m", "add foo", cwd=superp)

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
        _, out, err = cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
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

    def test_commit_sub_in_sub_dir(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=pjoin(superp, "foo"))

        self._gitoutput([giftp, "ls-tree", "-r", "--name-only", "HEAD"],
                        [
            ".gift",
            ".gift-refs",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=superp)

    def test_commit_sub_relative_git_dir(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args,
             "--git-dir=" + pjoin("..", "..", "supergit"),
             "--work-tree=..",
             "commit", "--sub",
             cwd=pjoin(superp, "foo"))

        self._gitoutput([giftp, "ls-tree", "-r", "--name-only", "HEAD"],
                        [
            ".gift",
            ".gift-refs",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=superp)

    def test_fetch_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)

        fetched_hash = cmd0(giftp, "rev-parse", "origin/master", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash)

    def test_fetch_sub_updates_super_ref(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        barhash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        # Record a foo/bar commit that only the next fetch brings in
        headhash = self._add_commit_to_bar_from_other_clone()
        refsp = pjoin(superp, ".gift-refs")
        refs = fread(refsp)
        refs = refs.replace(barhash, headhash)
        fwrite(refsp, refs)
        cmdx(giftp, *ident_args, "commit", "-m", "update .gift-refs", ".gift-refs", cwd=superp)

        cmdx(giftp, "fetch", "--sub", cwd=superp)
        superhead = cmd0(giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)
        self.assertEqual(headhash, superhead)

        cmdx(giftp, "reset", "--sub", "--hard", cwd=superp)
        barhead = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        self.assertEqual(headhash, barhead)

    def test_fetch_sub_recorded_commit(self):
        # .gift-refs records a foo/bar commit that is not pushed yet
        cmdx(origit, "clone", bargitp, barp)
        fwrite(pjoin(barp, "for_fetch"), "for_fetch")
        cmdx(origit, "add", "for_fetch", cwd=barp)
        cmdx(origit, *ident_args, "commit", "-m", "add for_fetch", cwd=barp)
        headhash = cmd0(origit, "rev-parse", "HEAD", cwd=barp)
        fwrite(pjoin(superp, ".gift-refs"), "- - foo/bar\n  - " + headhash + "\n")

        e = None
        try:
            cmdx(giftp, "init", "--sub", cwd=superp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(2, e.returncode)

        # Once it is pushed, fetch --sub brings it in, then checks it out
        cmdx(origit, "push", "origin", "master", cwd=barp)
        cmdx(giftp, "fetch", "--sub", cwd=subbarp)
        self.assertEqual(headhash, cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp))

    def test_fetch_sub_git_opts(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        # The sub-repo remotes are local paths, which this option forbids
        e = None
        try:
            cmdx(giftp, "-c", "protocol.file.allow=never", "fetch", "--sub", cwd=superp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(128, e.returncode)
        self.assertEqual(["fatal: transport 'file' not allowed"], e.err)

    def test_merge_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)
        cmdx(giftp, "merge", "--sub", cwd=superp)
        fetched_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash,
                         "HEAD is updated to latest master")

    def test_reset_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        ori_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)
        cmdx(giftp, "merge", "origin/master", cwd=subbarp)
        fetched_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash,
                         "HEAD is updated to latest master")

        cmdx(giftp, "reset", "--sub", cwd=superp)
        reset_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        self.assertEqual(ori_hash, reset_hash,
                         "HEAD is reset to original master")

    def _add_commit_to_bar_from_other_clone(self):
        cmdx(origit, "clone", bargitp, barp)

        fwrite(pjoin(barp, "for_fetch"), "for_fetch")
        cmdx(origit, "add", "for_fetch", cwd=barp)
        cmdx(origit, *ident_args, "commit", "-m", "add for_fetch", cwd=barp)
        cmdx(origit, "push", "origin", "master", cwd=barp)

        headhash = cmd0(origit, "rev-parse", "HEAD", cwd=barp)
        return headhash

    def test_op_in_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        superhash = cmd0(origit, "rev-parse", "HEAD", cwd=superp)
        dd(superhash)

        gift_super_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=superp)
        self.assertEqual(superhash, gift_super_hash,
                         "gift should get the right super HEAD hash")

        barhash = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        self.assertNotEqual(barhash, superhash,
                            "gift should get a different hash in sub dir bar")

        self._add_file_to_subbar()

        superhash2 = cmd0(origit, "rev-parse", "HEAD", cwd=superp)
        self.assertEqual(superhash, superhash2,
                         "commit in sub dir should not change super dir HEAD")

    def test_named_repo_in_sub(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        # clone needs no repo, so it works as in any other dir
        with tempfile.TemporaryDirectory() as tmpdir:
            cmdx(giftp, "clone", bargitp, pjoin(tmpdir, "x"), cwd=subbarp)
            self._fcontent("bar\n", tmpdir, "x", "bar")

        # A git dir and work tree named by the user are the repo to use
        named = ["--git-dir=" + supergitp, "--work-tree=" + superp]
        out = cmdout(giftp, *named, "log", "-1", "--format=%s", cwd=subbarp)
        self.assertEqual(["add super"], out)

        env = {"GIT_DIR": supergitp, "GIT_WORK_TREE": superp}
        out = cmdout(giftp, "log", "-1", "--format=%s", cwd=subbarp, env=env)
        self.assertEqual(["add super"], out)

        # Even with a broken .gift
        fwrite(pjoin(superp, ".gift"), "foo: 1\n")
        _, out, err = cmdx(giftp, *named, "log", "-1", "--format=%s", cwd=subbarp)
        self.assertEqual(["add super"], out)
        self.assertEqual(["GIFT: warning: .gift: expect dirs: {<dir>: <url>@<branch>, ...}"], err)

    def test_named_git_dir_forms_in_sub(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        fwrite(pjoin(subbarp, "bar"), "edited\n")

        # git reads both forms of --git-dir, and bargit is bare: it has no
        # work tree to reset, and foo/bar is not its work tree
        for named in (["--git-dir", bargitp], ["--git-dir=" + bargitp]):
            with self.assertRaises(CalledProcessError) as git_failure:
                cmdx(origit, *named, "reset", "--hard", cwd=subbarp)

            with self.assertRaises(CalledProcessError) as gift_failure:
                cmdx(giftp, *named, "reset", "--hard", cwd=subbarp)

            self.assertEqual(git_failure.exception.returncode, gift_failure.exception.returncode, named)
            self.assertEqual(git_failure.exception.err, gift_failure.exception.err, named)
            self._fcontent("edited\n", subbarp, "bar")

    def test_dot_dot_dir(self):
        # "..dep" is a dir in the work tree, not a path to the parent dir
        fwrite(pjoin(superp, ".gift"), "dirs:\n  ..dep: ../bargit@master\n")
        cmdx(giftp, "init", "--sub", cwd=superp)
        depp = pjoin(superp, "..dep")
        childp = pjoin(depp, "child")
        os.mkdir(childp)

        for cwd in (depp, childp):
            head = cmd0(giftp, "rev-parse", "HEAD", cwd=cwd)
            self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", head, cwd)

        # A command in ..dep changes the files of the sub-repo, not of super
        fwrite(pjoin(superp, "imsuperman"), "changed\n")
        fwrite(pjoin(depp, "bar"), "changed\n")
        cmdx(giftp, "reset", "-q", "--hard", cwd=childp)

        self._fcontent("changed\n", superp, "imsuperman")
        self._fcontent("bar\n", depp, "bar")
        self._fcontent("dirs:\n  ..dep: ../bargit@master\n", superp, ".gift")

        # With a broken .gift, the sub git dir tells that ..dep is a sub-repo
        fwrite(pjoin(superp, ".gift"), "foo: 1\n")
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "log", "-1", cwd=childp)

        self.assertEqual(2, failure.exception.returncode)
        self.assertEqual([".gift: expect dirs: {<dir>: <url>@<branch>, ...}"], failure.exception.err)

    def test_populate_super_ref(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        # commit --sub should populate super/head
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self._check_initial_superhead()

        self._add_file_to_subbar()
        self._remove_super_ref()

        # init --sub should populate super/head
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._check_initial_superhead()

    def test_populate_super_ref2(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        # commit --sub should populate super/head
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self._check_initial_superhead()

        head_of_bar = cmdx(giftp, "rev-parse",
                           "refs/remotes/super/head", cwd=subbarp)

        state0 = fread(pjoin(superp, ".gift-refs"))

        self._add_file_to_subbar()
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        head1 = cmdx(giftp, "rev-parse",
                     "refs/remotes/super/head", cwd=subbarp)
        self.assertNotEqual(head_of_bar, head1)

        state1 = fread(pjoin(superp, ".gift-refs"))
        self.assertNotEqual(state0, state1)

        # changing HEAD in super repo should repopulate super/head ref in sub repo
        cmdx(giftp, "reset", "HEAD~", cwd=superp)
        head2 = cmdx(giftp, "rev-parse",
                     "refs/remotes/super/head", cwd=subbarp)
        self.assertEqual(head_of_bar, head2)

    def test_super_checkout_should_populate_super_ref(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        head_of_bar = cmdx(giftp, "rev-parse",
                           "refs/remotes/super/head", cwd=subbarp)

        self._add_file_to_subbar()
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        head_of_bar1 = cmdx(giftp, "rev-parse",
                            "refs/remotes/super/head", cwd=subbarp)

        self.assertNotEqual(head_of_bar, head_of_bar1)

        # changing HEAD in super repo should repopulate super/head ref in sub repo
        cmdx(giftp, "checkout", "HEAD~", cwd=superp)
        head_of_bar_after_checkout = cmdx(
            giftp, "rev-parse", "refs/remotes/super/head", cwd=subbarp)

        self.assertEqual(head_of_bar, head_of_bar_after_checkout)

    def test_super_checkout_with_new_sub_repo(self):

        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        # The fixture commits .gift in an old format that gift can not parse
        cmdx(giftp, *ident_args, "commit", "-m", "update .gift", ".gift", cwd=superp)

        # "aaa" sorts first, so the first line of .gift-refs changes
        subaaap = pjoin(superp, "aaa")
        cmdx(giftp, *ident_args, "clone", "--sub",
             "../bargit@master", "aaa", cwd=superp)
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subaaap)
        self._remove_super_ref()

        # HEAD~2 is "update .gift", before "aaa" is added
        cmdx(giftp, "checkout", "HEAD~2", cwd=superp)
        self._check_initial_superhead()

        # .gift read before this checkout has no "aaa"
        cmdx(giftp, "checkout", "master", cwd=superp)
        aaa_head = cmd0(giftp, "rev-parse", "refs/remotes/super/head", cwd=subaaap)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", aaa_head)

    def test_unsupported_sub(self):
        e = None
        try:
            cmdx(giftp, "push", "--sub", cwd=superp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(2, e.returncode)
        self.assertEqual([], e.out)
        self.assertEqual(["--sub is not supported for: push"], e.err)

    def test_commit_sub_keeps_staged_changes(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        fwrite(pjoin(superp, "imsuperman"), "staged")
        cmdx(giftp, "add", "imsuperman", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        self._gitoutput([giftp, "diff", "--cached", "--name-only"],
                        ["imsuperman"], cwd=superp)
        self._gitoutput([giftp, "show", ":imsuperman"], ["staged"], cwd=superp)

    def test_commit_sub_skips_sub_tags(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, "tag", "bar-tag", cwd=subbarp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        self._gitoutput([giftp, "tag"], ["bar-tag"], cwd=subbarp)
        self._gitoutput([giftp, "tag"], [], cwd=superp)

    def test_commit_sub_unpushed(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._add_file_to_subbar()
        newbar = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        _, _, err = cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self.assertEqual([
            "GIFT: foo/bar: warning: commit " + newbar + " is not pushed to origin,"
            " so other clones can not check it out",
        ], err)

        # A fresh clone has no git dir for bar, and origin has no newbar
        force_remove(pjoin(supergitp, "gift", "subdir", "foo", "bar"))

        e = None
        try:
            cmdx(giftp, "init", "--sub", cwd=superp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(2, e.returncode)
        self.assertEqual(
            "foo/bar: can not find commit " + newbar + " recorded in .gift-refs;"
            " push it to origin from the clone that made it", e.err[-1])

    def test_bad_gift_entry(self):
        cases = [
            ("../bargit", "'../bargit'"),
            ("git@github.com:a/b.git", "'git@github.com:a/b.git'"),
            ("ssh://git@github.com/a/b.git", "'ssh://git@github.com/a/b.git'"),
            ("https://u@example.com/a/b.git", "'https://u@example.com/a/b.git'"),
            ("[bar, master]", "['bar', 'master']"),
            ('"@master"', "'@master'"),
        ]
        for entry, shown in cases:
            fwrite(pjoin(superp, ".gift"), "dirs:\n  foo/bar: " + entry + "\n")

            _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=superp)
            self.assertEqual(["add super"], out)
            self.assertEqual(["GIFT: warning: .gift: foo/bar: expect <url>@<branch>, got: " + shown], err)

    def test_broken_gift(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        fwrite(pjoin(superp, ".gift"), "dirs:\n  foo/bar: ../bargit@master\n")
        cmdx(origit, *ident_args, "commit", "-m", "update .gift", ".gift", cwd=superp)

        # Two branches each add a sub-repo, so a merge leaves .gift in conflict
        for branch in ("b1", "b2"):
            cmdx(origit, "checkout", "-b", branch, "master", cwd=superp)
            fwrite(pjoin(superp, ".gift"), "dirs:\n  foo/bar: ../bargit@master\n  " + branch + ": ../bargit@master\n")
            cmdx(origit, *ident_args, "commit", "-m", branch, ".gift", cwd=superp)

        e = None
        try:
            cmdx(origit, *ident_args, "-c", "merge.conflictStyle=merge", "merge", "b1", cwd=superp)
        except CalledProcessError as ee:
            e = ee
        self.assertEqual(1, e.returncode)

        conferr = ".gift: line 4: could not find expected ':'"

        # A --sub command, or a command in a sub-repo dir, still fails
        for cmds, cwd in ((["commit", "--sub"], superp), (["status"], subbarp)):
            e = None
            try:
                cmdx(giftp, *cmds, cwd=cwd)
            except CalledProcessError as ee:
                e = ee

            self.assertEqual(2, e.returncode, cmds)
            self.assertEqual([conferr], e.err, cmds)

        # Other commands run on the super repo, so they can resolve the conflict
        _, out, err = cmdx(giftp, "diff", "--name-only", "--diff-filter=U", cwd=superp)
        self.assertEqual([".gift"], out)
        self.assertEqual(["GIFT: warning: " + conferr], err)

        _, _, err = cmdx(giftp, "merge", "--abort", cwd=superp)
        self.assertEqual(["GIFT: warning: " + conferr], err)

        _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=superp)
        self.assertEqual(["b2"], out)
        self.assertEqual([], err)

        # An empty .gift has no sub-repo, and one without dirs: is broken
        fwrite(pjoin(superp, ".gift"), "")
        _, _, err = cmdx(giftp, "log", "-1", cwd=superp)
        self.assertEqual([], err)

        fwrite(pjoin(superp, ".gift"), "foo: 1\n")
        _, _, err = cmdx(giftp, "log", "-1", cwd=superp)
        self.assertEqual(["GIFT: warning: .gift: expect dirs: {<dir>: <url>@<branch>, ...}"], err)

    def test_unreadable_gift(self):
        if os.geteuid() == 0:
            self.skipTest("root reads a file without read permission")

        cmdx(giftp, "init", "--sub", cwd=superp)
        confp = pjoin(superp, ".gift")
        os.chmod(confp, 0)

        e = None
        try:
            cmdx(giftp, "log", "-1", "--format=%s", cwd=subbarp)
        except CalledProcessError as ee:
            e = ee

        # Out of a sub-repo dir, a command still runs on the super repo
        _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=superp)
        os.chmod(confp, 0o644)

        self.assertEqual(2, e.returncode)
        self.assertEqual([".gift: Permission denied"], e.err)
        self.assertEqual(["add super"], out)
        self.assertEqual(["GIFT: warning: .gift: Permission denied"], err)

    def test_undecodable_gift(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        # yaml reports a NUL byte without a line mark, and Python reports a
        # byte that is not UTF-8 before yaml reads the text
        cases = [
            (b"dirs: {}\n\0", ".gift: position 9: special characters are not allowed"),
            (b"dirs: {}\n# \xff\n", ".gift: 'utf-8' codec can't decode byte 0xff in position 11: invalid start byte"),
        ]
        for content, conferr in cases:
            with open(pjoin(superp, ".gift"), "wb") as f:
                f.write(content)

            e = None
            try:
                cmdx(giftp, "log", "-1", "--format=%s", cwd=subbarp)
            except CalledProcessError as ee:
                e = ee

            # Out of a sub-repo dir, a command still runs on the super repo
            _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=superp)

            self.assertEqual(2, e.returncode)
            self.assertEqual([conferr], e.err)
            self.assertEqual(["add super"], out)
            self.assertEqual(["GIFT: warning: " + conferr], err)

    def test_checkout_broken_gift(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "-m", "update .gift", ".gift", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self._add_file_to_subbar()
        newbar = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        fwrite(pjoin(superp, ".gift"), "foo: 1\n")
        cmdx(giftp, *ident_args, "commit", "-m", "break .gift", ".gift", cwd=superp)
        warning = "GIFT: warning: .gift: expect dirs: {<dir>: <url>@<branch>, ...}"

        # This checkout fixes .gift, so super/head follows .gift-refs
        _, _, err = cmdx(giftp, "checkout", "-q", "HEAD~2", cwd=superp)
        self.assertEqual([warning], err)
        self._check_initial_superhead()

        # This checkout breaks .gift, and the .gift read before it still works
        _, _, err = cmdx(giftp, "checkout", "-q", "master", cwd=superp)
        self.assertEqual([warning], err)

        # gift refuses to run in a sub-repo dir with a broken .gift
        bargitdir = pjoin(supergitp, "gift", "subdir", "foo", "bar")
        superhead = cmd0(origit, "--git-dir=" + bargitdir, "rev-parse", "refs/remotes/super/head")
        self.assertEqual(newbar, superhead)

    def test_bad_gift_dir(self):
        # superp/up leads out of the work tree
        os.symlink("..", pjoin(superp, "up"))

        for d in ("../x", "/x", "a/../../x", "up/x", ".", ".git/x", ".GIT/x", "a/.git"):
            fwrite(pjoin(superp, ".gift"), "dirs:\n  " + d + ": ../bargit@master\n")

            e = None
            try:
                cmdx(giftp, "init", "--sub", cwd=superp)
            except CalledProcessError as ee:
                e = ee

            self.assertEqual(2, e.returncode, d)
            self.assertEqual([".gift: '" + d + "': expect a dir inside the work tree and outside .git"], e.err, d)

        self.assertFalse(os.path.exists(pjoin(this_base, "testdata", "x")))

    def test_gift_dir_not_ref_name(self):
        # A ref name can not hold " " or a part with a leading "."
        fwrite(pjoin(superp, ".gift"), "dirs:\n  my dep: ../bargit@master\n  .dot/x: ../wowgit@master\n")
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        self._gitoutput([giftp, "ls-tree", "-r", "--name-only", "HEAD"],
                        [".dot/x/wow", ".gift", ".gift-refs", "imsuperman", "my dep/bar"], cwd=superp)
        self._gitoutput([origit, "for-each-ref", "--format=%(refname)", "refs/gift/sub"],
                        ["refs/gift/sub/%2Edot%2Fx", "refs/gift/sub/my%20dep"], cwd=superp)

    def test_gift_dir_with_git_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # The git dir is x/admin in the work tree
            os.mkdir(pjoin(tmpdir, "x"))
            cmdx(origit, "init", "--separate-git-dir=" + pjoin(tmpdir, "x", "admin"), cwd=tmpdir)

            for d in ("x", "x/admin", "x/admin/sub"):
                fwrite(pjoin(tmpdir, ".gift"), "dirs:\n  " + d + ": " + bargitp + "@master\n")

                e = None
                try:
                    cmdx(giftp, "init", "--sub", cwd=tmpdir)
                except CalledProcessError as ee:
                    e = ee

                self.assertEqual(2, e.returncode, d)
                self.assertEqual([".gift: '" + d + "': expect a dir inside the work tree and outside .git"], e.err, d)

            self._nofile(tmpdir, "x", "admin", "sub", "bar")

    def test_gift_dir_symlink(self):
        # superp/link leads to superp/nested/deep: the OS reads link/../../x
        # as superp/x, but git reads it as x beside superp
        os.makedirs(pjoin(superp, "nested", "deep"))
        os.symlink(pjoin("nested", "deep"), pjoin(superp, "link"))
        xp = pjoin(this_base, "testdata", "x")
        os.mkdir(xp)

        # A symlinked dir and an absolute path are other names of a dir
        for d in ("link/../../x", "link", pjoin(superp, "foo", "bar")):
            fwrite(pjoin(superp, ".gift"), "dirs:\n  " + d + ": ../bargit@master\n")

            e = None
            try:
                cmdx(giftp, "init", "--sub", cwd=superp)
            except CalledProcessError as ee:
                e = ee

            self.assertEqual(2, e.returncode, d)
            self.assertEqual([".gift: '" + d + "': expect a relative path without symlinks"], e.err, d)

        self.assertEqual([], os.listdir(xp))

    def test_gift_dir_alias(self):
        # ./foo/bar/ is foo/bar, where a command in subbarp finds it
        fwrite(pjoin(superp, ".gift"), "dirs:\n  ./foo/bar/: ../bargit@master\n")
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._gitoutput([giftp, "log", "-1", "--format=%s"], ["add bar"], cwd=subbarp)

        fwrite(pjoin(superp, ".gift"), "dirs:\n  foo/bar: ../bargit@master\n  ./foo/bar: ../wowgit@master\n")

        e = None
        try:
            cmdx(giftp, "init", "--sub", cwd=superp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(2, e.returncode)
        self.assertEqual([".gift: './foo/bar': dir 'foo/bar' is listed twice"], e.err)

    def test_nested_gift_dirs(self):
        head = cmd0(origit, "rev-parse", "HEAD", cwd=superp)
        index = cmdout(origit, "ls-files", "--stage", cwd=superp)

        for conf in ("dirs:\n  dep: ../bargit@master\n  dep/x/nested: ../wowgit@master\n",
                     "dirs:\n  dep/x/nested: ../wowgit@master\n  dep: ../bargit@master\n"):
            fwrite(pjoin(superp, ".gift"), conf)

            with self.assertRaises(CalledProcessError) as failure:
                cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

            self.assertEqual(2, failure.exception.returncode, conf)
            self.assertEqual([".gift: 'dep/x/nested' is inside sub-repo dir 'dep'"], failure.exception.err, conf)

        # No sub git dir, ref, index entry or commit is made
        self.assertFalse(os.path.exists(pjoin(supergitp, "gift")))
        self.assertEqual([], cmdout(origit, "for-each-ref", "refs/gift", cwd=superp))
        self.assertEqual(index, cmdout(origit, "ls-files", "--stage", cwd=superp))
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=superp))

        # A dir that only starts with the name of another is beside it
        fwrite(pjoin(superp, ".gift"), "dirs:\n  dep: ../bargit@master\n  dependency: ../wowgit@master\n")
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._fcontent("bar\n", superp, "dep", "bar")
        self._fcontent("wow\n", superp, "dependency", "wow")

    def test_relative_url_from_sub_dir(self):
        # ../bargit in .gift is relative to superp, not to subbarp
        os.makedirs(subbarp)
        cmdx(giftp, "status", cwd=subbarp)
        self._fcontent("bar\n", subbarp, "bar")

        headhash = self._add_commit_to_bar_from_other_clone()
        cmdx(giftp, "fetch", "--sub", cwd=subbarp)
        fetched_hash = cmd0(giftp, "rev-parse", "origin/master", cwd=subbarp)
        self.assertEqual(headhash, fetched_hash)

    def test_relative_url_without_dot(self):
        # up.git in .gift is relative to emptyp, not to dir1
        cmdx(giftp, "init", cwd=emptyp)
        cmdx(origit, "clone", "--bare", bargitp, pjoin(emptyp, "up.git"))
        fwrite(pjoin(emptyp, ".gift"), "dirs:\n  up: up.git@master\n")
        dir1 = pjoin(emptyp, "dir1")
        os.mkdir(dir1)

        cmdx(giftp, "init", "--sub", cwd=dir1)
        cmdx(giftp, "fetch", "--sub", cwd=dir1)

        self._fcontent("bar\n", emptyp, "up", "bar")
        self._gitoutput([giftp, "remote", "get-url", "origin"], [pjoin(emptyp, "up.git")], cwd=pjoin(emptyp, "up"))

    def test_changed_url(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        # wowgit stands in for a new url of bar
        wowgitp = pjoin(this_base, "testdata", "wowgit")
        fwrite(pjoin(superp, ".gift"),
               "dirs:\n  foo/bar: ../wowgit@master\n  foo/wow: ../wowgit@master\n")

        _, _, err = cmdx(giftp, "status", cwd=subbarp)
        self.assertEqual(["GIFT: foo/bar: set remote url: origin " + wowgitp], err)
        self._gitoutput([giftp, "remote", "get-url", "origin"], [wowgitp], cwd=subbarp)

        # A url rewritten by url.<base>.insteadOf is not a change
        insteadof = "url.file:///other/.insteadOf=" + this_base + "/"
        _, _, err = cmdx(giftp, "-c", insteadof, "status", cwd=subbarp)
        self.assertEqual([], err)

    def test_changed_branch(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        # bargit gets a branch dev with a new file, and foo/bar fetches it
        cmdx(origit, "clone", bargitp, barp)
        cmdx(origit, "checkout", "-b", "dev", cwd=barp)
        fwrite(pjoin(barp, "dev"), "dev")
        cmdx(origit, "add", "dev", cwd=barp)
        cmdx(origit, *ident_args, "commit", "-m", "add dev", cwd=barp)
        cmdx(origit, "push", "origin", "dev", cwd=barp)
        cmdx(giftp, "fetch", cwd=subbarp)

        fwrite(pjoin(superp, ".gift"), "dirs:\n  foo/bar: ../bargit@dev\n  foo/wow: ../wowgit@master\n")

        # Local changes keep foo/bar on master
        fwrite(pjoin(subbarp, "bar"), "changed")
        _, _, err = cmdx(giftp, "status", cwd=subbarp)
        self.assertEqual([
            "GIFT: foo/bar: warning: .gift changed the branch from master to dev,"
            " but the work tree has local changes",
        ], err)
        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subbarp)

        # A clean foo/bar moves to dev
        fwrite(pjoin(subbarp, "bar"), "bar\n")
        _, _, err = cmdx(giftp, "status", cwd=subbarp)
        self.assertEqual(["GIFT: foo/bar: .gift changed the branch from master to dev: checkout dev"], err)
        self._fcontent("dev", subbarp, "dev")
        self._gitoutput([giftp, "rev-parse", "--abbrev-ref", "@{upstream}"], ["origin/dev"], cwd=subbarp)

        # A branch that the user checks out later stays
        cmdx(giftp, "checkout", "master", cwd=subbarp)
        _, _, err = cmdx(giftp, "status", cwd=subbarp)
        self.assertEqual([], err)
        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subbarp)

        # Without a record, as from an older gift, foo/bar is taken as set
        bargitdir = pjoin(supergitp, "gift", "subdir", "foo", "bar")
        cmdx(origit, "--git-dir=" + bargitdir, "config", "--unset", "gift.branch")
        _, _, err = cmdx(giftp, "status", cwd=subbarp)
        self.assertEqual([], err)
        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subbarp)
        self._gitoutput([origit, "--git-dir=" + bargitdir, "config", "gift.branch"], ["dev"])

    def test_no_gift_file_skips_refs(self):
        # emptyp has no .gift, so gift runs no extra git process for .gift-refs
        cmdx(giftp, "init", cwd=emptyp)

        cmds = self._git_trace("checkout", "-q", "-b", "x", cwd=emptyp)
        self.assertEqual([
            "git rev-parse --absolute-git-dir --show-toplevel",
            "git checkout -q -b x",
        ], cmds)

    def test_head_fixed_cmd_skips_refs(self):
        # log never moves HEAD, so gift reads no .gift-refs for it
        cmds = self._git_trace("log", "-1", "--oneline", cwd=superp)
        self.assertEqual([
            "git rev-parse --absolute-git-dir --show-toplevel",
            "git log -1 --oneline",
        ], cmds)

        cmds = self._git_trace("reset", "-q", cwd=superp)
        self.assertEqual([
            "git rev-parse --absolute-git-dir --show-toplevel",
            "git show HEAD:.gift-refs",
            "git reset -q",
            "git show HEAD:.gift-refs",
        ], cmds)

    def test_commit_sub_args(self):
        cmdx(giftp, "init", "--sub", cwd=superp)

        cmdx(giftp, *ident_args, "commit", "--sub", "-m", "add subs", cwd=superp)
        self._gitoutput([giftp, "log", "-1", "--format=%s"], ["add subs"], cwd=superp)
        head = cmd0(giftp, "rev-parse", "HEAD", cwd=superp)

        _, _, err = cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self.assertEqual(["GIFT: nothing to commit: no sub-repo changed"], err)
        self._gitoutput([giftp, "rev-parse", "HEAD"], [head], cwd=superp)

        e = None
        try:
            cmdx(giftp, *ident_args, "commit", "--sub", "--amend", cwd=superp)
        except CalledProcessError as ee:
            e = ee

        self.assertEqual(2, e.returncode)
        self.assertEqual(["commit --sub accepts only -m <msg>, got: --amend"], e.err)

    def test_sub_args(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)
        self._add_file_to_subbar()
        newbar = cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp)

        modes = "--soft, --mixed, -N, --hard, --merge, --keep, -q, --quiet"
        cases = [
            (["init", "--sub", "x"], "init --sub accepts no argument, got: x"),
            (["fetch", "--sub", "nosuchremote"], "fetch --sub accepts no argument, got: nosuchremote"),
            (["merge", "--sub", "nosuchbranch"], "merge --sub accepts no argument, got: nosuchbranch"),
            (["reset", "--sub", "--hard", "HEAD"], "reset --sub accepts only " + modes + ", got: HEAD"),
            (["clone", "--sub", "../bargit@master"], "usage: gift clone --sub <url>@<branch> <dir>"),
        ]
        for cmds, msg in cases:
            e = None
            try:
                cmdx(giftp, *cmds, cwd=superp)
            except CalledProcessError as ee:
                e = ee

            self.assertEqual(2, e.returncode, cmds)
            self.assertEqual([msg], e.err, cmds)

        # reset --sub did not move foo/bar back to super/head
        self.assertEqual(newbar, cmd0(giftp, "rev-parse", "HEAD", cwd=subbarp))

    def test_init_sub_branch_from_gift(self):
        cmdx(giftp, "init", "--sub", cwd=superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=superp)

        # As in a fresh clone, init bar from .gift-refs, with another default branch
        force_remove(pjoin(supergitp, "gift", "subdir", "foo", "bar"))
        env = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "init.defaultBranch",
            "GIT_CONFIG_VALUE_0": "main",
        }
        cmdx(giftp, "init", "--sub", cwd=superp, env=env)

        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=subbarp)

    def test_malformed_gift_refs(self):
        bar_ref = "- [foo/bar, 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af]\n"
        usage = ".gift-refs: expect a list of [<dir>, <commit>], got: "
        cases = [
            ("42\n", usage + "42"),
            ("- foo/bar\n", usage + "'foo/bar'"),
            ("- [foo/bar]\n", usage + "['foo/bar']"),
            ("- [foo/bar, 42]\n", usage + "['foo/bar', 42]"),
            ("- [foo/bar, --hard]\n", usage + "['foo/bar', '--hard']"),
            (bar_ref + bar_ref, ".gift-refs: dir 'foo/bar' is listed twice"),
        ]
        for content, msg in cases:
            fwrite(pjoin(superp, ".gift-refs"), content)

            e = None
            try:
                cmdx(giftp, "init", "--sub", cwd=superp)
            except CalledProcessError as ee:
                e = ee

            self.assertEqual(2, e.returncode, content)
            self.assertEqual(msg, e.err[-1], content)

        # An empty .gift-refs records no commit
        fwrite(pjoin(superp, ".gift-refs"), "")
        cmdx(giftp, "init", "--sub", cwd=superp)
        self._fcontent("bar\n", subbarp, "bar")

        # A malformed .gift-refs in HEAD only warns
        fwrite(pjoin(superp, ".gift-refs"), "42\n")
        cmdx(origit, "add", ".gift-refs", cwd=superp)
        cmdx(origit, *ident_args, "commit", "-m", "bad refs", cwd=superp)
        _, _, err = cmdx(giftp, "fetch", "--sub", cwd=superp)
        self.assertEqual(["GIFT: can not parse .gift-refs in HEAD:", usage + "42"], err[-2:])

    def test_bad_gift_refs(self):
        fwrite(pjoin(superp, ".gift-refs"), "- [foo/bar\n")
        cmdx(origit, "add", ".gift-refs", cwd=superp)
        cmdx(origit, *ident_args, "commit", "-m", "bad refs", cwd=superp)

        # The error goes to stderr once, and not to stdout
        _, out, err = cmdx(giftp, "reset", "-q", "HEAD", cwd=superp)
        self.assertEqual([], out)

        gift_lines = [line for line in err if line.startswith("GIFT: ")]
        self.assertEqual(["GIFT: can not parse .gift-refs in HEAD:"], gift_lines)


class TestGitSubrepo(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = tmp.name

        # git-subrepo commits on HEAD, so the repo needs a commit
        cmdx(origit, "init", self.repo)
        cmdx(origit, "config", "user.name", "fooUser", cwd=self.repo)
        cmdx(origit, "config", "user.email", "my@email.org", cwd=self.repo)
        cmdx(origit, "commit", "--allow-empty", "-m", "init", cwd=self.repo)

    def _update(self, conf):
        fwrite(pjoin(self.repo, ".gitsubrepo"), conf)
        return cmdf(subrepop, cwd=self.repo)

    def test_update(self):
        # Run by its shebang, git-subrepo reads bash syntax such as ${a:0:1}
        code, _, err = self._update("bar " + bargitp + " master\n")
        self.assertEqual(0, code, err)
        self.assertEqual("bar\n", fread(pjoin(self.repo, "bar", "bar")))

    def test_url_is_data(self):
        # ${prefix} in a url is the dir
        code, _, err = self._update("bargit " + pjoin(this_base, "testdata") + "/${prefix} master\n")
        self.assertEqual(0, code, err)
        self.assertEqual("bar\n", fread(pjoin(self.repo, "bargit", "bar")))

        # Other shell syntax in a url is not run
        self._update("dep $(touch${IFS}marker) master\n")
        self.assertFalse(os.path.exists(pjoin(self.repo, "marker")))

    def test_url_is_not_option(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        markerp = pjoin(tmp.name, "marker")
        helperp = pjoin(tmp.name, "helper")
        fwrite(helperp, "#!/bin/sh\ntouch " + markerp + "\nexit 1\n")
        os.chmod(helperp, 0o755)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.repo)

        # git must not read the url as --upload-pack, which runs the helper
        code, _, _ = self._update("dep --upload-pack=" + helperp + " " + bargitp + "\n")

        self.assertEqual(1, code)
        self.assertFalse(os.path.exists(markerp))
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.repo))

    def test_tag_per_dir(self):
        # "." in a dir must not turn into a char that another dir has: each
        # dir is fetched into its own tag
        wowgitp = pjoin(this_base, "testdata", "wowgit")
        code, _, err = self._update("foo.bar " + bargitp + " master\nfoo-bar " + wowgitp + " master\n")
        self.assertEqual(0, code, err)

        paths = cmdout(origit, "ls-tree", "-r", "--name-only", "HEAD", cwd=self.repo)
        self.assertEqual(["foo-bar/wow", "foo.bar/bar"], paths)
        self.assertEqual(["bar"], cmdout(origit, "show", "HEAD:foo.bar/bar", cwd=self.repo))
        self.assertEqual(["wow"], cmdout(origit, "show", "HEAD:foo-bar/wow", cwd=self.repo))

    def test_failed_fetch(self):
        code, _, _ = self._update("bar " + bargitp + " master\nnosuch " + pjoin(self.repo, "nosuch") + " master\n")
        self.assertEqual(1, code)

        # bar is not imported, and its fetched tag is removed
        self.assertFalse(os.path.exists(pjoin(self.repo, "bar")))
        self.assertEqual([], cmdout(origit, "for-each-ref", "refs/tags", cwd=self.repo))


def force_remove(fn):

    try:
        shutil.rmtree(fn)
    except BaseException:
        pass

    try:
        os.unlink(fn)
    except BaseException:
        pass
