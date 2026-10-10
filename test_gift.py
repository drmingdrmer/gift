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

import pytest
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

execpath = cmd0(origit, '--exec-path')

ident_args = [
        '-c', 'user.name=fooUser',
        '-c', 'user.email=my@email.org',
]


class BaseTest(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def _testdata(self, tmp_path):
        # Each test changes its own copy of testdata. pytest removes it after
        # the test passes, see tmp_path_retention_policy in pytest.ini
        self.base = str(tmp_path)
        print("files of this test:", self.base)
        shutil.copytree(pjoin(this_base, "testdata"), pjoin(self.base, "testdata"))

        self.emptyp = pjoin(self.base, "testdata", "empty")
        self.superp = pjoin(self.base, "testdata", "super")
        self.supergitp = pjoin(self.base, "testdata", "supergit")
        self.subbarp = pjoin(self.base, "testdata", "super", "foo", "bar")
        self.subwowp = pjoin(self.base, "testdata", "super", "foo", "wow")
        self.bargitp = pjoin(self.base, "testdata", "bargit")
        self.barp = pjoin(self.base, "testdata", "bar")

    def setUp(self):
        self.maxDiff = None

        # .git can not be track in a git repo.
        # need to manually create it.
        fwrite(pjoin(self.base, "testdata", "super", ".git"),
               "gitdir: ../supergit")

    def _remove_super_ref(self):
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=self.subbarp)
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=self.subwowp)

    def _check_initial_superhead(self):
        _, out, _ = cmdx(giftp, "rev-parse",
                         "refs/remotes/super/head", cwd=self.subbarp)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", out[0])

        _, out, _ = cmdx(giftp, "rev-parse",
                         "refs/remotes/super/head", cwd=self.subwowp)
        self.assertEqual("6bf37e52cbafcf55ff4710bb2b63309b55bf8e54", out[0])

    def _add_file_to_subbar(self):
        fwrite(pjoin(self.subbarp, "newbar"), "newbar")
        cmdx(giftp, "add", "newbar", cwd=self.subbarp)
        cmdx(giftp, *ident_args, "commit", "-m", "add newbar", cwd=self.subbarp)

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
            'startpath': [self.superp],
            'git_dir': None,
            'work_tree': None,
        }))
        gg.init_git_config()

        rel, sb = gg.get_subrepo_config(pjoin(self.superp, "f"))
        self.assertEqual(('', None), (rel, sb), "inexistent path")

        rel, sb = gg.get_subrepo_config(pjoin(self.superp, "foo"))
        self.assertEqual(('', None), (rel, sb), "inexistent path foo")

        rel, sb = gg.get_subrepo_config(pjoin(self.superp, "foo/bar"))
        self.assertEqual('foo/bar', rel)
        self.assertEqual({
            'bareenv': {'GIT_DIR': self.base + '/testdata/supergit/gift/subdir/foo/bar'},
            'dir': 'foo/bar',
            'env': {'GIT_DIR': self.base + '/testdata/supergit/gift/subdir/foo/bar',
                    'GIT_WORK_TREE': self.base + '/testdata/super/foo/bar'},
            'refhead': 'refs/gift/sub/foo%2Fbar',
            'sub_gitdir': 'gift/subdir/foo/bar',
            'upstream': {'branch': 'master', 'name': 'origin', 'url': self.base + '/testdata/bargit'}
        }, sb)


class TestGiftParse(unittest.TestCase):

    def test_parse_remote(self):
        gg = Gift(GitOpt().update({
            'startpath': [],
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

    def test_parse_refs(self):
        bar = "466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af"
        wow = "6bf37e52cbafcf55ff4710bb2b63309b55bf8e54"
        sha256 = "ab" * 32
        cases = {
            "": [],
            "[]\n": [],
            "- [foo/bar, " + bar + "]\n": [["foo/bar", bar]],
            # As gift writes it
            "- - foo/bar\n  - " + bar + "\n- - foo/wow\n  - " + wow + "\n": [["foo/bar", bar], ["foo/wow", wow]],
            "- [foo/bar, " + sha256 + "]\n": [["foo/bar", sha256]],
        }
        got = {content: gift.parse_refs(content) for content in cases}
        self.assertEqual(cases, got)

        usage = ".gift-refs: expect a list of [<dir>, <commit>], got: "
        errors = {
            "42\n": usage + "42",
            "- foo/bar\n": usage + "'foo/bar'",
            "- [foo/bar]\n": usage + "['foo/bar']",
            "- [foo/bar, " + bar + ", x]\n": usage + "['foo/bar', '" + bar + "', 'x']",
            "- [42, " + bar + "]\n": usage + "[42, '" + bar + "']",
            "- [foo/bar, 42]\n": usage + "['foo/bar', 42]",
            # Only a full commit id, which git can not read as an option
            "- [foo/bar, --hard]\n": usage + "['foo/bar', '--hard']",
            "- [foo/bar, 466f0bb]\n": usage + "['foo/bar', '466f0bb']",
            "- [foo/bar, " + bar + "]\n- [foo/bar, " + wow + "]\n": ".gift-refs: dir 'foo/bar' is listed twice",
        }
        got = {}
        for content in errors:
            with self.assertRaises(gift.GiftError, msg=content) as failure:
                gift.parse_refs(content)
            got[content] = str(failure.exception)
        self.assertEqual(errors, got)

        # yaml describes a syntax error in several lines, after the file name
        with self.assertRaises(gift.GiftError) as failure:
            gift.parse_refs("- [foo/bar\n")
        first_line = str(failure.exception).splitlines()[0]
        self.assertEqual(".gift-refs: while parsing a flow sequence", first_line)


class TestGiftPartialInit(BaseTest):

    def setUp(self):
        super(TestGiftPartialInit, self).setUp()

        gg = Gift(GitOpt().update({
            'startpath': [self.superp],
            'git_dir': None,
            'work_tree': None,

        }))
        gg.init_git_config()

        rel, sb = gg.get_subrepo_config(pjoin(self.superp, "foo/bar"))
        self.gg = gg
        self.sb = sb
        self.rel = rel

    def test_init_1_with_inited(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._fcontent("bar\n", self.subbarp, "bar")

    def test_init_2_with_remote(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])
        cmdx(origit, "remote", "add", self.sb['upstream']['name'],
             self.sb['upstream']['url'], env=self.sb['bareenv'])

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._fcontent("bar\n", self.subbarp, "bar")

    def test_init_3_with_fetched(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])
        cmdx(origit, "remote", "add", self.sb['upstream']['name'],
             self.sb['upstream']['url'], env=self.sb['bareenv'])
        cmdx(origit, "fetch", self.sb['upstream']
             ['name'], env=self.sb['bareenv'], cwd=self.superp)

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._fcontent("bar\n", self.subbarp, "bar")

    def test_init_4_already_checkout(self):

        cmdx(origit, "init", "--bare", self.sb['env']['GIT_DIR'])
        cmdx(origit, "remote", "add", self.sb['upstream']['name'],
             self.sb['upstream']['url'], env=self.sb['bareenv'])
        cmdx(origit, "fetch", self.sb['upstream']
             ['name'], env=self.sb['bareenv'], cwd=self.superp)

        os.makedirs(self.sb['env']['GIT_WORK_TREE'], mode=0o755)
        cmdx(origit, "checkout",
             self.sb['upstream']['branch'], env=self.sb['env'])
        self._fcontent("bar\n", self.subbarp, "bar")

        os.unlink(pjoin(self.subbarp, "bar"))

        # init --sub should not checkout again to modify work tree
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._nofile(self.subbarp, "bar")


class TestGiftDelegate(BaseTest):

    def test_opt_version(self):
        out = cmdout(giftp, "--version", cwd=self.superp)
        self.assertEqual('gift version 0.2.0', out[0])
        self.assertEqual(2, len(out))

    def test_opt_help(self):
        out = cmdout(giftp, "--help", cwd=self.superp)
        self.assertIn(
            'These are common Git commands used in various situations:', out)
        self.assertIn('Gift extended command:', out)
        self.assertIn('gift clone --sub <url>@<branch> <dir>', out)

    def test_opt_paging(self):
        out = cmdout(giftp, "gift-debug", cwd=self.superp)
        self.assertIn('paging: null', '\n'.join(out))

        out = cmdout(giftp, '-p', "gift-debug", cwd=self.superp)
        self.assertIn('paging: true', '\n'.join(out))

        out = cmdout(giftp, '--paginate', "gift-debug", cwd=self.superp)
        self.assertIn('paging: true', '\n'.join(out))

        out = cmdout(giftp, '--no-pager', "gift-debug", cwd=self.superp)
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
                     "-p", "gift-debug", cwd=self.superp)
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
            'evaluated cwd: ' + self.base + '/testdata/super',
            'evaluated git_dir: None',
            'evaluated working_dir: None',
        ], out)

    def test_opt_minus_c(self):
        code, out, err = cmdtty(
            giftp, "-c", "pager.log=head -n 1", "log", "--no-color", cwd=self.superp)
        self.assertEqual(0, code)
        self.assertEqual([
            'commit c3954c897dfe40a5b99b7145820eeb227210265c (HEAD -> master)'
        ], out)
        self.assertEqual([], err)

    def test_opt_git_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = cmdout(giftp, '--git-dir=' + self.supergitp,
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
                         '--git-dir=' + self.supergitp,
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
                         '--git-dir=' + self.supergitp,
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
                         '-C', self.base,
                         '--git-dir=' + pjoin('testdata', 'supergit'),
                         '--work-tree=' + pjoin("testdata", 'super'),
                         "ls-files",
                         cwd=tmpdir)

        self.assertEqual(['.gift', 'imsuperman'], out)

        out = cmdout(giftp, '-C', pjoin('testdata', 'super'),
                     "log", "-1", "--format=%s", cwd=self.base)
        self.assertEqual(['add super'], out)

    def test_opt_big_c_sub_gitdir(self):
        # emptyp/.git is a dir, so `git rev-parse --git-dir` prints ".git"
        cmdx(giftp, "init", cwd=self.emptyp)

        with tempfile.TemporaryDirectory() as tmpdir:
            cmdx(giftp, *ident_args, '-C', self.emptyp, "clone", "--sub",
                 "../bargit@master", "bar", cwd=tmpdir)
            self.assertFalse(os.path.exists(pjoin(tmpdir, ".git")))

        self.assertTrue(os.path.isdir(pjoin(self.emptyp, ".git", "gift", "subdir", "bar")))

    def test_opt_big_c_init(self):
        os.mkdir(pjoin(self.base, "newrepo"))
        cmdx(giftp, '-C', "newrepo", "init", cwd=self.base)

        self.assertFalse(os.path.exists(pjoin(self.base, ".git")))
        self.assertTrue(os.path.isdir(pjoin(self.base, "newrepo", ".git")))

    def test_opt_big_c_missing_dir(self):
        missing = pjoin(self.superp, "nosuchdir")
        want = ["fatal: cannot change to '" + missing + "': No such file or directory"]

        # A git command, an informative command, and no command
        for cmds in (["status"], ["--version"], []):
            with self.assertRaises(CalledProcessError, msg=cmds) as failure:
                cmdx(giftp, '-C', "nosuchdir", *cmds, cwd=self.superp)
            e = failure.exception

            self.assertEqual(128, e.returncode, cmds)
            self.assertEqual([], e.out, cmds)
            self.assertEqual(want, e.err, cmds)

    def test_env_git_dir(self):
        out = cmdout(giftp, "log", "-1", "--format=%s",
                     cwd=self.base, env={"GIT_DIR": self.bargitp})
        self.assertEqual(['add bar'], out)

    def test_error_output(self):
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "abc")
        e = failure.exception

        self.assertEqual(1, e.returncode)
        self.assertEqual([], e.out)
        self.assertEqual(
            "git: 'abc' is not a git command. See 'git --help'.", e.err[0])

        # there should not raw python error returned
        self.assertNotIn('Traceback', "".join(e.out))
        self.assertNotIn('Traceback', "".join(e.err))

    def test_no_cmd(self):
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp)
        e = failure.exception

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
            origit, "log", "-n1", "c3954c897dfe40a5b99b7145820eeb227210265c", cwd=self.superp)

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
            giftp, "log", "-n1", "c3954c897dfe40a5b99b7145820eeb227210265c", cwd=self.superp)

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

        cmdx(giftp, "log", "-n1", cwd=self.supergitp)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "commit", "--sub", cwd=self.supergitp)
        e = failure.exception
        self.assertEqual(2, e.returncode)
        self.assertEqual([], e.out)
        self.assertEqual(
            ["--sub can not be used in git-dir:" + self.supergitp], e.err)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "status", cwd=self.supergitp)
        e = failure.exception
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
        cmdx(giftp, "clone", self.bargitp, "bar", cwd=self.base)
        self._gitoutput([giftp, "ls-files"], [
            "bar"
        ], cwd=pjoin(self.base, 'bar'))

        self._fcontent("bar\n", self.base, "bar/bar")

    def test_clone_in_other_repo(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        cmdx(giftp, "clone", "../bargit", "bar", cwd=self.emptyp)
        self._gitoutput([giftp, "ls-files"], [
            "bar"
        ], cwd=pjoin(self.emptyp, "bar"))

        self._fcontent("bar\n", self.emptyp, "bar/bar")

    def test_clone_sub(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        code, out, err = cmdx(giftp, *ident_args,  "clone", "--sub",
                              "../bargit@master", "path/to/bar", cwd=self.emptyp)
        for l in (
                'GIFT: path/to/bar: add remote: origin ' + self.bargitp,
                'GIFT: path/to/bar: fetch origin ' + self.bargitp,
                "From " + self.bargitp,
        ):
            self.assertIn(l, "\n".join(err),
                          "it should output fetching status")

        self._gitoutput([giftp, "ls-files"], [
            ".gift",
            ".gift-refs",
            "path/to/bar/bar",
        ], cwd=self.emptyp)

        self._fcontent(
            "dirs:\n  path/to/bar: ../bargit@master\n", self.emptyp, ".gift")
        self._fcontent("\n".join([
            "- - path/to/bar",
            "  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af",
            "",
        ]), self.emptyp, ".gift-refs")
        self._fcontent("bar\n", self.emptyp, "path/to/bar/bar")

    def test_clone_sub_failed(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        confp = pjoin(self.emptyp, ".gift")
        bad_gitdir = pjoin(self.emptyp, ".git", "gift", "subdir", "bad")

        # A bad url, before any .gift exists
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../nosuch@master", "bad", cwd=self.emptyp)
        e = failure.exception

        self.assertEqual(128, e.returncode)
        self.assertFalse(os.path.exists(confp))
        self.assertEqual([], cmdout(origit, "rev-list", "--all", cwd=self.emptyp))
        self.assertFalse(os.path.exists(bad_gitdir))

        # A bad branch, with .gift from an earlier clone --sub
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "bar", cwd=self.emptyp)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@nosuch", "bad", cwd=self.emptyp)
        e = failure.exception

        self.assertEqual(1, e.returncode)
        self._fcontent("dirs:\n  bar: ../bargit@master\n", confp)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp))
        self.assertFalse(os.path.exists(bad_gitdir))

        # A dir that is already a sub-repo
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "bar", cwd=self.emptyp)
        e = failure.exception

        self.assertEqual(2, e.returncode)
        self.assertEqual(["clone --sub: bar is already a sub-repo in .gift"], e.err)
        self._fcontent("dirs:\n  bar: ../bargit@master\n", confp)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp))

        cmdx(giftp, "init", "--sub", cwd=self.emptyp)

    def test_clone_sub_failed_commit(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "bar", cwd=self.emptyp)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp)
        index = cmdout(origit, "ls-files", "--stage", ".gift", ".gift-refs", cwd=self.emptyp)

        hookp = pjoin(self.emptyp, ".git", "hooks", "pre-commit")
        fwrite(hookp, "#!/bin/sh\nexit 1\n")
        os.chmod(hookp, 0o755)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "wow", cwd=self.emptyp)

        self.assertEqual(1, failure.exception.returncode)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp))
        self.assertEqual(index, cmdout(origit, "ls-files", "--stage", ".gift", ".gift-refs", cwd=self.emptyp))
        self._fcontent("dirs:\n  bar: ../bargit@master\n", self.emptyp, ".gift")
        self._fcontent("- - bar\n  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af\n", self.emptyp, ".gift-refs")
        self.assertFalse(os.path.exists(pjoin(self.emptyp, "wow")))
        self.assertFalse(os.path.exists(pjoin(self.emptyp, ".git", "gift", "subdir", "wow")))

        # Without the hook, the same clone works
        os.unlink(hookp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "wow", cwd=self.emptyp)

        self._fcontent("dirs:\n  bar: ../bargit@master\n  wow: ../wowgit@master\n", self.emptyp, ".gift")
        self._fcontent("wow\n", self.emptyp, "wow", "wow")

    def test_clone_sub_dropped_dir(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "bar", cwd=self.emptyp)

        # Dropped from .gift, bar keeps its sub git dir, with the HEAD of bargit
        fwrite(pjoin(self.emptyp, ".gift"), "dirs: {}\n")
        cmdx(origit, *ident_args, "commit", "-m", "drop bar", ".gift", cwd=self.emptyp)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "bar", cwd=self.emptyp)
        e = failure.exception

        bar_gitdir = pjoin(self.emptyp, ".git", "gift", "subdir", "bar")
        self.assertEqual(2, e.returncode)
        self.assertEqual(["clone --sub: an old sub-repo in bar left its git dir: " + bar_gitdir], e.err)
        self._fcontent("dirs: {}\n", self.emptyp, ".gift")
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.emptyp))

        bar_url = cmd0(origit, "--git-dir", bar_gitdir, "remote", "get-url", "origin")
        self.assertEqual(self.bargitp, bar_url)

        # Without the old sub git dir, .gift-refs still records the bargit
        # commit for bar. A failed clone keeps that entry.
        force_remove(bar_gitdir)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@nosuch", "bar", cwd=self.emptyp)
        e = failure.exception

        self.assertEqual(1, e.returncode)
        self._fcontent("- - bar\n  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af\n", self.emptyp, ".gift-refs")

        # The clone checks out wowgit, and the commit that adds bar to .gift
        # drops the old entry
        cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "bar", cwd=self.emptyp)
        added_refs = cmdout(origit, "show", "HEAD~:.gift-refs", cwd=self.emptyp)

        self._fcontent("wow\n", self.emptyp, "bar", "wow")
        self._fcontent("- - bar\n  - 6bf37e52cbafcf55ff4710bb2b63309b55bf8e54\n", self.emptyp, ".gift-refs")
        self.assertEqual(["[]"], added_refs)

    def test_clone_sub_in_dropped_dir(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        cmdx(giftp, *ident_args, "clone", "--sub", "../bargit@master", "dep", cwd=self.emptyp)

        # Dropped from .gift, dep keeps its ref in the super repo
        fwrite(pjoin(self.emptyp, ".gift"), "dirs: {}\n")
        cmdx(origit, *ident_args, "commit", "-m", "drop dep", ".gift", cwd=self.emptyp)

        cmdx(giftp, *ident_args, "clone", "--sub", "../wowgit@master", "dep/child", cwd=self.emptyp)
        tree = cmdout(origit, "ls-tree", "-r", "--name-only", "HEAD", cwd=self.emptyp)

        self._fcontent("dirs:\n  dep/child: ../wowgit@master\n", self.emptyp, ".gift")
        self._fcontent("- - dep/child\n  - 6bf37e52cbafcf55ff4710bb2b63309b55bf8e54\n", self.emptyp, ".gift-refs")
        self.assertEqual([".gift", ".gift-refs", "dep/bar", "dep/child/wow"], tree)
        self.assertEqual(["wow"], cmdout(origit, "show", "HEAD:dep/child/wow", cwd=self.emptyp))

    def test_clone_sub_in_sub_dir(self):
        cmdx(giftp, "init", cwd=self.emptyp)
        cmdx(origit, "clone", "--bare", self.bargitp, pjoin(self.emptyp, "up.git"))
        dir1 = pjoin(self.emptyp, "dir1")
        os.mkdir(dir1)
        cmdx(origit, "clone", "--bare", self.bargitp, pjoin(dir1, "here.git"))

        # As git clone does, <dir> and a relative <url> are read from the cwd
        cmdx(giftp, *ident_args, "clone", "--sub", "../../bargit@master", "bar", cwd=dir1)
        cmdx(giftp, *ident_args, "clone", "--sub", "../up.git@master", "up", cwd=dir1)
        cmdx(giftp, *ident_args, "clone", "--sub", "here.git@master", "here", cwd=dir1)

        self._fcontent("dirs:\n  dir1/bar: ../bargit@master\n  dir1/here: ./dir1/here.git@master\n"
                       "  dir1/up: ./up.git@master\n", self.emptyp, ".gift")
        self._fcontent("bar\n", dir1, "bar", "bar")
        self._fcontent("bar\n", dir1, "up", "bar")
        self._fcontent("bar\n", dir1, "here", "bar")

    def test_init_sub(self):
        self._nofile(self.subbarp, "bar")
        self._nofile(self.subwowp, "wow")

        for _ in range(2):
            cmdx(giftp, "init", "--sub", cwd=self.superp)

            self._fcontent("bar\n", self.subbarp, "bar")
            self._fcontent("wow\n", self.subwowp, "wow")

            self._gitoutput([giftp, "symbolic-ref", "--short",
                             "HEAD"], ["master"], cwd=self.subbarp)
            self._gitoutput([giftp, "symbolic-ref", "--short",
                             "HEAD"], ["master"], cwd=self.subwowp)
            self._gitoutput([giftp, "ls-files"],
                            [".gift", "imsuperman"], cwd=self.superp)

    def test_init_sub_with_git_env(self):
        env = {"GIT_DIR": self.supergitp, "GIT_WORK_TREE": self.superp}
        cmdx(giftp, "init", "--sub", cwd=self.superp, env=env)

        self._fcontent("bar\n", self.subbarp, "bar")
        self._fcontent("wow\n", self.subwowp, "wow")

    def test_init_sub_with_files_from_super(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self._add_commit_to_bar_from_other_clone()

        # A fresh clone of super has the files of bar, but no git dir for bar
        force_remove(pjoin(self.supergitp, "gift", "subdir", "foo", "bar"))

        # It should adopt the commit in .gift-refs and keep the files
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        bar_head = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", bar_head)

        self._gitoutput([giftp, "status", "--porcelain"], [], cwd=self.subbarp)
        self._gitoutput([giftp, "rev-parse", "--abbrev-ref", "@{upstream}"],
                        ["origin/master"], cwd=self.subbarp)

    def test_commit_in_super(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, "add", "foo", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "-m", "add foo", cwd=self.superp)

        self._gitoutput([giftp, "ls-files"],
                        [
            ".gift",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=self.superp)

    def test_commit_sub(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        _, out, err = cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
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
            cwd=self.superp)

        self._fcontent(
            "\n".join(["- - foo/bar",
                       "  - 466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af",
                       "- - foo/wow",
                       "  - 6bf37e52cbafcf55ff4710bb2b63309b55bf8e54",
                       ""]),
            self.superp, ".gift-refs",
        )

    def test_commit_sub_in_sub_dir(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=pjoin(self.superp, "foo"))

        self._gitoutput([giftp, "ls-tree", "-r", "--name-only", "HEAD"],
                        [
            ".gift",
            ".gift-refs",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=self.superp)

    def test_commit_sub_relative_git_dir(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args,
             "--git-dir=" + pjoin("..", "..", "supergit"),
             "--work-tree=..",
             "commit", "--sub",
             cwd=pjoin(self.superp, "foo"))

        self._gitoutput([giftp, "ls-tree", "-r", "--name-only", "HEAD"],
                        [
            ".gift",
            ".gift-refs",
            "foo/bar/bar",
            "foo/wow/wow",
            "imsuperman",
        ],
            cwd=self.superp)

    def test_fetch_sub(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=self.superp)

        fetched_hash = cmd0(giftp, "rev-parse", "origin/master", cwd=self.subbarp)

        self.assertEqual(headhash, fetched_hash)

    def test_fetch_sub_updates_super_ref(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        barhash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)

        # Record a foo/bar commit that only the next fetch brings in
        headhash = self._add_commit_to_bar_from_other_clone()
        refsp = pjoin(self.superp, ".gift-refs")
        refs = fread(refsp)
        refs = refs.replace(barhash, headhash)
        fwrite(refsp, refs)
        cmdx(giftp, *ident_args, "commit", "-m", "update .gift-refs", ".gift-refs", cwd=self.superp)

        cmdx(giftp, "fetch", "--sub", cwd=self.superp)
        superhead = cmd0(giftp, "rev-parse", "refs/remotes/super/head", cwd=self.subbarp)
        self.assertEqual(headhash, superhead)

        cmdx(giftp, "reset", "--sub", "--hard", cwd=self.superp)
        barhead = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)
        self.assertEqual(headhash, barhead)

    def test_fetch_sub_recorded_commit(self):
        # .gift-refs records a foo/bar commit that is not pushed yet
        cmdx(origit, "clone", self.bargitp, self.barp)
        fwrite(pjoin(self.barp, "for_fetch"), "for_fetch")
        cmdx(origit, "add", "for_fetch", cwd=self.barp)
        cmdx(origit, *ident_args, "commit", "-m", "add for_fetch", cwd=self.barp)
        headhash = cmd0(origit, "rev-parse", "HEAD", cwd=self.barp)
        fwrite(pjoin(self.superp, ".gift-refs"), "- - foo/bar\n  - " + headhash + "\n")

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "init", "--sub", cwd=self.superp)
        e = failure.exception

        self.assertEqual(2, e.returncode)

        # Once it is pushed, fetch --sub brings it in, then checks it out
        cmdx(origit, "push", "origin", "master", cwd=self.barp)
        cmdx(giftp, "fetch", "--sub", cwd=self.subbarp)
        self.assertEqual(headhash, cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp))

    def test_fetch_sub_git_opts(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # The sub-repo remotes are local paths, which this option forbids
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "-c", "protocol.file.allow=never", "fetch", "--sub", cwd=self.superp)
        e = failure.exception

        self.assertEqual(128, e.returncode)
        self.assertEqual(["fatal: transport 'file' not allowed"], e.err)

    def test_merge_sub(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=self.superp)
        cmdx(giftp, "merge", "--sub", cwd=self.superp)
        fetched_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)

        self.assertEqual(headhash, fetched_hash,
                         "HEAD is updated to latest master")

    def test_reset_sub(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        ori_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=self.superp)
        cmdx(giftp, "merge", "origin/master", cwd=self.subbarp)
        fetched_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)

        self.assertEqual(headhash, fetched_hash,
                         "HEAD is updated to latest master")

        cmdx(giftp, "reset", "--sub", cwd=self.superp)
        reset_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)
        self.assertEqual(ori_hash, reset_hash,
                         "HEAD is reset to original master")

    def _add_commit_to_bar_from_other_clone(self):
        cmdx(origit, "clone", self.bargitp, self.barp)

        fwrite(pjoin(self.barp, "for_fetch"), "for_fetch")
        cmdx(origit, "add", "for_fetch", cwd=self.barp)
        cmdx(origit, *ident_args, "commit", "-m", "add for_fetch", cwd=self.barp)
        cmdx(origit, "push", "origin", "master", cwd=self.barp)

        headhash = cmd0(origit, "rev-parse", "HEAD", cwd=self.barp)
        return headhash

    def test_op_in_sub(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)

        superhash = cmd0(origit, "rev-parse", "HEAD", cwd=self.superp)
        dd(superhash)

        gift_super_hash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.superp)
        self.assertEqual(superhash, gift_super_hash,
                         "gift should get the right super HEAD hash")

        barhash = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)
        self.assertNotEqual(barhash, superhash,
                            "gift should get a different hash in sub dir bar")

        self._add_file_to_subbar()

        superhash2 = cmd0(origit, "rev-parse", "HEAD", cwd=self.superp)
        self.assertEqual(superhash, superhash2,
                         "commit in sub dir should not change super dir HEAD")

    def test_named_repo_in_sub(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # clone needs no repo, so it works as in any other dir
        cmdx(giftp, "clone", self.bargitp, pjoin(self.base, "x"), cwd=self.subbarp)
        self._fcontent("bar\n", self.base, "x", "bar")

        # A git dir and work tree named by the user are the repo to use
        named = ["--git-dir=" + self.supergitp, "--work-tree=" + self.superp]
        out = cmdout(giftp, *named, "log", "-1", "--format=%s", cwd=self.subbarp)
        self.assertEqual(["add super"], out)

        env = {"GIT_DIR": self.supergitp, "GIT_WORK_TREE": self.superp}
        out = cmdout(giftp, "log", "-1", "--format=%s", cwd=self.subbarp, env=env)
        self.assertEqual(["add super"], out)

        # Even with a broken .gift
        fwrite(pjoin(self.superp, ".gift"), "foo: 1\n")
        _, out, err = cmdx(giftp, *named, "log", "-1", "--format=%s", cwd=self.subbarp)
        self.assertEqual(["add super"], out)
        self.assertEqual(["GIFT: warning: .gift: expect dirs: {<dir>: <url>@<branch>, ...}"], err)

    def test_named_git_dir_forms_in_sub(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        fwrite(pjoin(self.subbarp, "bar"), "edited\n")

        # git reads both forms of --git-dir, and bargit is bare: it has no
        # work tree to reset, and foo/bar is not its work tree
        for named in (["--git-dir", self.bargitp], ["--git-dir=" + self.bargitp]):
            with self.assertRaises(CalledProcessError, msg=named) as git_failure:
                cmdx(origit, *named, "reset", "--hard", cwd=self.subbarp)

            with self.assertRaises(CalledProcessError, msg=named) as gift_failure:
                cmdx(giftp, *named, "reset", "--hard", cwd=self.subbarp)

            self.assertEqual(git_failure.exception.returncode, gift_failure.exception.returncode, named)
            self.assertEqual(git_failure.exception.err, gift_failure.exception.err, named)
            self._fcontent("edited\n", self.subbarp, "bar")

    def test_dot_dot_dir(self):
        # "..dep" is a dir in the work tree, not a path to the parent dir
        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  ..dep: ../bargit@master\n")
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        depp = pjoin(self.superp, "..dep")
        childp = pjoin(depp, "child")
        os.mkdir(childp)

        for cwd in (depp, childp):
            head = cmd0(giftp, "rev-parse", "HEAD", cwd=cwd)
            self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", head, cwd)

        # A command in ..dep changes the files of the sub-repo, not of super
        fwrite(pjoin(self.superp, "imsuperman"), "changed\n")
        fwrite(pjoin(depp, "bar"), "changed\n")
        cmdx(giftp, "reset", "-q", "--hard", cwd=childp)

        self._fcontent("changed\n", self.superp, "imsuperman")
        self._fcontent("bar\n", depp, "bar")
        self._fcontent("dirs:\n  ..dep: ../bargit@master\n", self.superp, ".gift")

        # With a broken .gift, the sub git dir tells that ..dep is a sub-repo
        fwrite(pjoin(self.superp, ".gift"), "foo: 1\n")
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "log", "-1", cwd=childp)

        self.assertEqual(2, failure.exception.returncode)
        self.assertEqual([".gift: expect dirs: {<dir>: <url>@<branch>, ...}"], failure.exception.err)

    def test_populate_super_ref(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # commit --sub should populate super/head
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self._check_initial_superhead()

        self._add_file_to_subbar()
        self._remove_super_ref()

        # init --sub should populate super/head
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._check_initial_superhead()

    def test_populate_super_ref2(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # commit --sub should populate super/head
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self._check_initial_superhead()

        head_of_bar = cmdx(giftp, "rev-parse",
                           "refs/remotes/super/head", cwd=self.subbarp)

        state0 = fread(pjoin(self.superp, ".gift-refs"))

        self._add_file_to_subbar()
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        head1 = cmdx(giftp, "rev-parse",
                     "refs/remotes/super/head", cwd=self.subbarp)
        self.assertNotEqual(head_of_bar, head1)

        state1 = fread(pjoin(self.superp, ".gift-refs"))
        self.assertNotEqual(state0, state1)

        # changing HEAD in super repo should repopulate super/head ref in sub repo
        cmdx(giftp, "reset", "HEAD~", cwd=self.superp)
        head2 = cmdx(giftp, "rev-parse",
                     "refs/remotes/super/head", cwd=self.subbarp)
        self.assertEqual(head_of_bar, head2)

    def test_super_checkout_should_populate_super_ref(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        head_of_bar = cmdx(giftp, "rev-parse",
                           "refs/remotes/super/head", cwd=self.subbarp)

        self._add_file_to_subbar()
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        head_of_bar1 = cmdx(giftp, "rev-parse",
                            "refs/remotes/super/head", cwd=self.subbarp)

        self.assertNotEqual(head_of_bar, head_of_bar1)

        # changing HEAD in super repo should repopulate super/head ref in sub repo
        cmdx(giftp, "checkout", "HEAD~", cwd=self.superp)
        head_of_bar_after_checkout = cmdx(
            giftp, "rev-parse", "refs/remotes/super/head", cwd=self.subbarp)

        self.assertEqual(head_of_bar, head_of_bar_after_checkout)

    def test_super_checkout_with_new_sub_repo(self):

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        # The fixture commits .gift in an old format that gift can not parse
        cmdx(giftp, *ident_args, "commit", "-m", "update .gift", ".gift", cwd=self.superp)

        # "aaa" sorts first, so the first line of .gift-refs changes
        subaaap = pjoin(self.superp, "aaa")
        cmdx(giftp, *ident_args, "clone", "--sub",
             "../bargit@master", "aaa", cwd=self.superp)
        cmdx(giftp, "update-ref", "-d", "refs/remotes/super/head", cwd=subaaap)
        self._remove_super_ref()

        # HEAD~2 is "update .gift", before "aaa" is added
        cmdx(giftp, "checkout", "HEAD~2", cwd=self.superp)
        self._check_initial_superhead()

        # .gift read before this checkout has no "aaa"
        cmdx(giftp, "checkout", "master", cwd=self.superp)
        aaa_head = cmd0(giftp, "rev-parse", "refs/remotes/super/head", cwd=subaaap)
        self.assertEqual("466f0bbdf56b1428edf2aed4f6a99c1bd1d4c8af", aaa_head)

    def test_unsupported_sub(self):
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "push", "--sub", cwd=self.superp)
        e = failure.exception

        self.assertEqual(2, e.returncode)
        self.assertEqual([], e.out)
        self.assertEqual(["--sub is not supported for: push"], e.err)

    def test_commit_sub_keeps_staged_changes(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        fwrite(pjoin(self.superp, "imsuperman"), "staged")
        cmdx(giftp, "add", "imsuperman", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        self._gitoutput([giftp, "diff", "--cached", "--name-only"],
                        ["imsuperman"], cwd=self.superp)
        self._gitoutput([giftp, "show", ":imsuperman"], ["staged"], cwd=self.superp)

    def test_commit_sub_skips_sub_tags(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, "tag", "bar-tag", cwd=self.subbarp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        self._gitoutput([giftp, "tag"], ["bar-tag"], cwd=self.subbarp)
        self._gitoutput([giftp, "tag"], [], cwd=self.superp)

    def test_commit_sub_unpushed(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._add_file_to_subbar()
        newbar = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)

        _, _, err = cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self.assertEqual([
            "GIFT: foo/bar: warning: commit " + newbar + " is not pushed to origin,"
            " so other clones can not check it out",
        ], err)

        # A fresh clone has no git dir for bar, and origin has no newbar
        force_remove(pjoin(self.supergitp, "gift", "subdir", "foo", "bar"))

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "init", "--sub", cwd=self.superp)
        e = failure.exception

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
            fwrite(pjoin(self.superp, ".gift"), "dirs:\n  foo/bar: " + entry + "\n")

            _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=self.superp)
            self.assertEqual(["add super"], out)
            self.assertEqual(["GIFT: warning: .gift: foo/bar: expect <url>@<branch>, got: " + shown], err)

    def test_broken_gift(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  foo/bar: ../bargit@master\n")
        cmdx(origit, *ident_args, "commit", "-m", "update .gift", ".gift", cwd=self.superp)

        # Two branches each add a sub-repo, so a merge leaves .gift in conflict
        for branch in ("b1", "b2"):
            cmdx(origit, "checkout", "-b", branch, "master", cwd=self.superp)
            fwrite(pjoin(self.superp, ".gift"), "dirs:\n  foo/bar: ../bargit@master\n  " + branch + ": ../bargit@master\n")
            cmdx(origit, *ident_args, "commit", "-m", branch, ".gift", cwd=self.superp)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(origit, *ident_args, "-c", "merge.conflictStyle=merge", "merge", "b1", cwd=self.superp)
        e = failure.exception
        self.assertEqual(1, e.returncode)

        conferr = ".gift: line 4: could not find expected ':'"

        # A --sub command, or a command in a sub-repo dir, still fails
        for cmds, cwd in ((["commit", "--sub"], self.superp), (["status"], self.subbarp)):
            with self.assertRaises(CalledProcessError, msg=cmds) as failure:
                cmdx(giftp, *cmds, cwd=cwd)
            e = failure.exception

            self.assertEqual(2, e.returncode, cmds)
            self.assertEqual([conferr], e.err, cmds)

        # Other commands run on the super repo, so they can resolve the conflict
        _, out, err = cmdx(giftp, "diff", "--name-only", "--diff-filter=U", cwd=self.superp)
        self.assertEqual([".gift"], out)
        self.assertEqual(["GIFT: warning: " + conferr], err)

        _, _, err = cmdx(giftp, "merge", "--abort", cwd=self.superp)
        self.assertEqual(["GIFT: warning: " + conferr], err)

        _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=self.superp)
        self.assertEqual(["b2"], out)
        self.assertEqual([], err)

        # An empty .gift has no sub-repo, and one without dirs: is broken
        fwrite(pjoin(self.superp, ".gift"), "")
        _, _, err = cmdx(giftp, "log", "-1", cwd=self.superp)
        self.assertEqual([], err)

        fwrite(pjoin(self.superp, ".gift"), "foo: 1\n")
        _, _, err = cmdx(giftp, "log", "-1", cwd=self.superp)
        self.assertEqual(["GIFT: warning: .gift: expect dirs: {<dir>: <url>@<branch>, ...}"], err)

    def test_unreadable_gift(self):
        if os.geteuid() == 0:
            self.skipTest("root reads a file without read permission")

        cmdx(giftp, "init", "--sub", cwd=self.superp)
        confp = pjoin(self.superp, ".gift")
        os.chmod(confp, 0)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "log", "-1", "--format=%s", cwd=self.subbarp)
        e = failure.exception

        # Out of a sub-repo dir, a command still runs on the super repo
        _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=self.superp)
        os.chmod(confp, 0o644)

        self.assertEqual(2, e.returncode)
        self.assertEqual([".gift: Permission denied"], e.err)
        self.assertEqual(["add super"], out)
        self.assertEqual(["GIFT: warning: .gift: Permission denied"], err)

    def test_undecodable_gift(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # yaml reports a NUL byte without a line mark, and Python reports a
        # byte that is not UTF-8 before yaml reads the text
        cases = [
            (b"dirs: {}\n\0", ".gift: position 9: special characters are not allowed"),
            (b"dirs: {}\n# \xff\n", ".gift: 'utf-8' codec can't decode byte 0xff in position 11: invalid start byte"),
        ]
        for content, conferr in cases:
            with open(pjoin(self.superp, ".gift"), "wb") as f:
                f.write(content)

            with self.assertRaises(CalledProcessError, msg=content) as failure:
                cmdx(giftp, "log", "-1", "--format=%s", cwd=self.subbarp)
            e = failure.exception

            # Out of a sub-repo dir, a command still runs on the super repo
            _, out, err = cmdx(giftp, "log", "-1", "--format=%s", cwd=self.superp)

            self.assertEqual(2, e.returncode)
            self.assertEqual([conferr], e.err)
            self.assertEqual(["add super"], out)
            self.assertEqual(["GIFT: warning: " + conferr], err)

    def test_checkout_broken_gift(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "-m", "update .gift", ".gift", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self._add_file_to_subbar()
        newbar = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        fwrite(pjoin(self.superp, ".gift"), "foo: 1\n")
        cmdx(giftp, *ident_args, "commit", "-m", "break .gift", ".gift", cwd=self.superp)
        warning = "GIFT: warning: .gift: expect dirs: {<dir>: <url>@<branch>, ...}"

        # This checkout fixes .gift, so super/head follows .gift-refs
        _, _, err = cmdx(giftp, "checkout", "-q", "HEAD~2", cwd=self.superp)
        self.assertEqual([warning], err)
        self._check_initial_superhead()

        # This checkout breaks .gift, and the .gift read before it still works
        _, _, err = cmdx(giftp, "checkout", "-q", "master", cwd=self.superp)
        self.assertEqual([warning], err)

        # gift refuses to run in a sub-repo dir with a broken .gift
        bargitdir = pjoin(self.supergitp, "gift", "subdir", "foo", "bar")
        superhead = cmd0(origit, "--git-dir=" + bargitdir, "rev-parse", "refs/remotes/super/head")
        self.assertEqual(newbar, superhead)

    def test_bad_gift_dir(self):
        # superp/up leads out of the work tree
        os.symlink("..", pjoin(self.superp, "up"))

        for d in ("../x", "/x", "a/../../x", "up/x", ".", ".git/x", ".GIT/x", "a/.git"):
            fwrite(pjoin(self.superp, ".gift"), "dirs:\n  " + d + ": ../bargit@master\n")

            with self.assertRaises(CalledProcessError, msg=d) as failure:
                cmdx(giftp, "init", "--sub", cwd=self.superp)
            e = failure.exception

            self.assertEqual(2, e.returncode, d)
            self.assertEqual([".gift: '" + d + "': expect a dir inside the work tree and outside .git"], e.err, d)

        self.assertFalse(os.path.exists(pjoin(self.base, "testdata", "x")))

    def test_gift_dir_not_ref_name(self):
        # A ref name can not hold " " or a part with a leading "."
        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  my dep: ../bargit@master\n  .dot/x: ../wowgit@master\n")
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        self._gitoutput([giftp, "ls-tree", "-r", "--name-only", "HEAD"],
                        [".dot/x/wow", ".gift", ".gift-refs", "imsuperman", "my dep/bar"], cwd=self.superp)
        self._gitoutput([origit, "for-each-ref", "--format=%(refname)", "refs/gift/sub"],
                        ["refs/gift/sub/%2Edot%2Fx", "refs/gift/sub/my%20dep"], cwd=self.superp)

    def test_gift_dir_with_git_dir(self):
        tmpdir = pjoin(self.base, "repo")

        # The git dir is x/admin in the work tree
        os.makedirs(pjoin(tmpdir, "x"))
        cmdx(origit, "init", "--separate-git-dir=" + pjoin(tmpdir, "x", "admin"), cwd=tmpdir)

        for d in ("x", "x/admin", "x/admin/sub"):
            fwrite(pjoin(tmpdir, ".gift"), "dirs:\n  " + d + ": " + self.bargitp + "@master\n")

            with self.assertRaises(CalledProcessError, msg=d) as failure:
                cmdx(giftp, "init", "--sub", cwd=tmpdir)
            e = failure.exception

            self.assertEqual(2, e.returncode, d)
            self.assertEqual([".gift: '" + d + "': expect a dir inside the work tree and outside .git"], e.err, d)

        self._nofile(tmpdir, "x", "admin", "sub", "bar")

    def test_gift_dir_symlink(self):
        # superp/link leads to superp/nested/deep: the OS reads link/../../x
        # as superp/x, but git reads it as x beside superp
        os.makedirs(pjoin(self.superp, "nested", "deep"))
        os.symlink(pjoin("nested", "deep"), pjoin(self.superp, "link"))
        xp = pjoin(self.base, "testdata", "x")
        os.mkdir(xp)

        # A symlinked dir and an absolute path are other names of a dir
        for d in ("link/../../x", "link", pjoin(self.superp, "foo", "bar")):
            fwrite(pjoin(self.superp, ".gift"), "dirs:\n  " + d + ": ../bargit@master\n")

            with self.assertRaises(CalledProcessError, msg=d) as failure:
                cmdx(giftp, "init", "--sub", cwd=self.superp)
            e = failure.exception

            self.assertEqual(2, e.returncode, d)
            self.assertEqual([".gift: '" + d + "': expect a relative path without symlinks"], e.err, d)

        self.assertEqual([], os.listdir(xp))

    def test_gift_dir_alias(self):
        # ./foo/bar/ is foo/bar, where a command in subbarp finds it
        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  ./foo/bar/: ../bargit@master\n")
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._gitoutput([giftp, "log", "-1", "--format=%s"], ["add bar"], cwd=self.subbarp)

        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  foo/bar: ../bargit@master\n  ./foo/bar: ../wowgit@master\n")

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "init", "--sub", cwd=self.superp)
        e = failure.exception

        self.assertEqual(2, e.returncode)
        self.assertEqual([".gift: './foo/bar': dir 'foo/bar' is listed twice"], e.err)

    def test_nested_gift_dirs(self):
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.superp)
        index = cmdout(origit, "ls-files", "--stage", cwd=self.superp)

        for conf in ("dirs:\n  dep: ../bargit@master\n  dep/x/nested: ../wowgit@master\n",
                     "dirs:\n  dep/x/nested: ../wowgit@master\n  dep: ../bargit@master\n"):
            fwrite(pjoin(self.superp, ".gift"), conf)

            with self.assertRaises(CalledProcessError, msg=conf) as failure:
                cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

            self.assertEqual(2, failure.exception.returncode, conf)
            self.assertEqual([".gift: 'dep/x/nested' is inside sub-repo dir 'dep'"], failure.exception.err, conf)

        # No sub git dir, ref, index entry or commit is made
        self.assertFalse(os.path.exists(pjoin(self.supergitp, "gift")))
        self.assertEqual([], cmdout(origit, "for-each-ref", "refs/gift", cwd=self.superp))
        self.assertEqual(index, cmdout(origit, "ls-files", "--stage", cwd=self.superp))
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.superp))

        # A dir that only starts with the name of another is beside it
        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  dep: ../bargit@master\n  dependency: ../wowgit@master\n")
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._fcontent("bar\n", self.superp, "dep", "bar")
        self._fcontent("wow\n", self.superp, "dependency", "wow")

    def test_relative_url_from_sub_dir(self):
        # ../bargit in .gift is relative to superp, not to subbarp
        os.makedirs(self.subbarp)
        cmdx(giftp, "status", cwd=self.subbarp)
        self._fcontent("bar\n", self.subbarp, "bar")

        headhash = self._add_commit_to_bar_from_other_clone()
        cmdx(giftp, "fetch", "--sub", cwd=self.subbarp)
        fetched_hash = cmd0(giftp, "rev-parse", "origin/master", cwd=self.subbarp)
        self.assertEqual(headhash, fetched_hash)

    def test_relative_url_without_dot(self):
        # up.git in .gift is relative to emptyp, not to dir1
        cmdx(giftp, "init", cwd=self.emptyp)
        cmdx(origit, "clone", "--bare", self.bargitp, pjoin(self.emptyp, "up.git"))
        fwrite(pjoin(self.emptyp, ".gift"), "dirs:\n  up: up.git@master\n")
        dir1 = pjoin(self.emptyp, "dir1")
        os.mkdir(dir1)

        cmdx(giftp, "init", "--sub", cwd=dir1)
        cmdx(giftp, "fetch", "--sub", cwd=dir1)

        self._fcontent("bar\n", self.emptyp, "up", "bar")
        self._gitoutput([giftp, "remote", "get-url", "origin"], [pjoin(self.emptyp, "up.git")], cwd=pjoin(self.emptyp, "up"))

    def test_changed_url(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # wowgit stands in for a new url of bar
        wowgitp = pjoin(self.base, "testdata", "wowgit")
        fwrite(pjoin(self.superp, ".gift"),
               "dirs:\n  foo/bar: ../wowgit@master\n  foo/wow: ../wowgit@master\n")

        _, _, err = cmdx(giftp, "status", cwd=self.subbarp)
        self.assertEqual(["GIFT: foo/bar: set remote url: origin " + wowgitp], err)
        self._gitoutput([giftp, "remote", "get-url", "origin"], [wowgitp], cwd=self.subbarp)

        # A url rewritten by url.<base>.insteadOf is not a change
        insteadof = "url.file:///other/.insteadOf=" + self.base + "/"
        _, _, err = cmdx(giftp, "-c", insteadof, "status", cwd=self.subbarp)
        self.assertEqual([], err)

    def test_changed_branch(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        # bargit gets a branch dev with a new file, and foo/bar fetches it
        cmdx(origit, "clone", self.bargitp, self.barp)
        cmdx(origit, "checkout", "-b", "dev", cwd=self.barp)
        fwrite(pjoin(self.barp, "dev"), "dev")
        cmdx(origit, "add", "dev", cwd=self.barp)
        cmdx(origit, *ident_args, "commit", "-m", "add dev", cwd=self.barp)
        cmdx(origit, "push", "origin", "dev", cwd=self.barp)
        cmdx(giftp, "fetch", cwd=self.subbarp)

        fwrite(pjoin(self.superp, ".gift"), "dirs:\n  foo/bar: ../bargit@dev\n  foo/wow: ../wowgit@master\n")

        # Local changes keep foo/bar on master
        fwrite(pjoin(self.subbarp, "bar"), "changed")
        _, _, err = cmdx(giftp, "status", cwd=self.subbarp)
        self.assertEqual([
            "GIFT: foo/bar: warning: .gift changed the branch from master to dev,"
            " but the work tree has local changes",
        ], err)
        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=self.subbarp)

        # A clean foo/bar moves to dev
        fwrite(pjoin(self.subbarp, "bar"), "bar\n")
        _, _, err = cmdx(giftp, "status", cwd=self.subbarp)
        self.assertEqual(["GIFT: foo/bar: .gift changed the branch from master to dev: checkout dev"], err)
        self._fcontent("dev", self.subbarp, "dev")
        self._gitoutput([giftp, "rev-parse", "--abbrev-ref", "@{upstream}"], ["origin/dev"], cwd=self.subbarp)

        # A branch that the user checks out later stays
        cmdx(giftp, "checkout", "master", cwd=self.subbarp)
        _, _, err = cmdx(giftp, "status", cwd=self.subbarp)
        self.assertEqual([], err)
        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=self.subbarp)

        # Without a record, as from an older gift, foo/bar is taken as set
        bargitdir = pjoin(self.supergitp, "gift", "subdir", "foo", "bar")
        cmdx(origit, "--git-dir=" + bargitdir, "config", "--unset", "gift.branch")
        _, _, err = cmdx(giftp, "status", cwd=self.subbarp)
        self.assertEqual([], err)
        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=self.subbarp)
        self._gitoutput([origit, "--git-dir=" + bargitdir, "config", "gift.branch"], ["dev"])

    def test_no_gift_file_skips_refs(self):
        # emptyp has no .gift, so gift runs no extra git process for .gift-refs
        cmdx(giftp, "init", cwd=self.emptyp)

        cmds = self._git_trace("checkout", "-q", "-b", "x", cwd=self.emptyp)
        self.assertEqual([
            "git rev-parse --absolute-git-dir --show-toplevel",
            "git checkout -q -b x",
        ], cmds)

    def test_head_fixed_cmd_skips_refs(self):
        # log never moves HEAD, so gift reads no .gift-refs for it
        cmds = self._git_trace("log", "-1", "--oneline", cwd=self.superp)
        self.assertEqual([
            "git rev-parse --absolute-git-dir --show-toplevel",
            "git log -1 --oneline",
        ], cmds)

        cmds = self._git_trace("reset", "-q", cwd=self.superp)
        self.assertEqual([
            "git rev-parse --absolute-git-dir --show-toplevel",
            "git show HEAD:.gift-refs",
            "git reset -q",
            "git show HEAD:.gift-refs",
        ], cmds)

    def test_commit_sub_args(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)

        cmdx(giftp, *ident_args, "commit", "--sub", "-m", "add subs", cwd=self.superp)
        self._gitoutput([giftp, "log", "-1", "--format=%s"], ["add subs"], cwd=self.superp)
        head = cmd0(giftp, "rev-parse", "HEAD", cwd=self.superp)

        _, _, err = cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self.assertEqual(["GIFT: nothing to commit: no sub-repo changed"], err)
        self._gitoutput([giftp, "rev-parse", "HEAD"], [head], cwd=self.superp)

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, *ident_args, "commit", "--sub", "--amend", cwd=self.superp)
        e = failure.exception

        self.assertEqual(2, e.returncode)
        self.assertEqual(["commit --sub accepts only -m <msg>, got: --amend"], e.err)

    def test_sub_args(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)
        self._add_file_to_subbar()
        newbar = cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp)

        modes = "--soft, --mixed, -N, --hard, --merge, --keep, -q, --quiet"
        cases = [
            (["init", "--sub", "x"], "init --sub accepts no argument, got: x"),
            (["fetch", "--sub", "nosuchremote"], "fetch --sub accepts no argument, got: nosuchremote"),
            (["merge", "--sub", "nosuchbranch"], "merge --sub accepts no argument, got: nosuchbranch"),
            (["reset", "--sub", "--hard", "HEAD"], "reset --sub accepts only " + modes + ", got: HEAD"),
            (["clone", "--sub", "../bargit@master"], "usage: gift clone --sub <url>@<branch> <dir>"),
        ]
        for cmds, msg in cases:
            with self.assertRaises(CalledProcessError, msg=cmds) as failure:
                cmdx(giftp, *cmds, cwd=self.superp)
            e = failure.exception

            self.assertEqual(2, e.returncode, cmds)
            self.assertEqual([msg], e.err, cmds)

        # reset --sub did not move foo/bar back to super/head
        self.assertEqual(newbar, cmd0(giftp, "rev-parse", "HEAD", cwd=self.subbarp))

    def test_init_sub_branch_from_gift(self):
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        cmdx(giftp, *ident_args, "commit", "--sub", cwd=self.superp)

        # As in a fresh clone, init bar from .gift-refs, with another default branch
        force_remove(pjoin(self.supergitp, "gift", "subdir", "foo", "bar"))
        env = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "init.defaultBranch",
            "GIT_CONFIG_VALUE_0": "main",
        }
        cmdx(giftp, "init", "--sub", cwd=self.superp, env=env)

        self._gitoutput([giftp, "symbolic-ref", "--short", "HEAD"], ["master"], cwd=self.subbarp)

    def test_malformed_gift_refs(self):
        # test_parse_refs checks each kind of malformed content. This test
        # checks each state of the repos in which gift reads .gift-refs.
        usage = ".gift-refs: expect a list of [<dir>, <commit>], got: "

        # A fresh init reads .gift-refs before it checks out a sub-repo
        fwrite(pjoin(self.superp, ".gift-refs"), "42\n")

        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "init", "--sub", cwd=self.superp)
        e = failure.exception

        self.assertEqual(2, e.returncode)
        self.assertEqual(usage + "42", e.err[-1])

        # After the user fixes .gift-refs, the same init works. An empty
        # .gift-refs records no commit.
        fwrite(pjoin(self.superp, ".gift-refs"), "")
        cmdx(giftp, "init", "--sub", cwd=self.superp)
        self._fcontent("bar\n", self.subbarp, "bar")

        # A malformed .gift-refs in HEAD only warns
        fwrite(pjoin(self.superp, ".gift-refs"), "42\n")
        cmdx(origit, "add", ".gift-refs", cwd=self.superp)
        cmdx(origit, *ident_args, "commit", "-m", "bad refs", cwd=self.superp)
        _, _, err = cmdx(giftp, "fetch", "--sub", cwd=self.superp)
        self.assertEqual(["GIFT: can not parse .gift-refs in HEAD:", usage + "42"], err[-2:])

        # With the sub-repos checked out, init --sub still reads .gift-refs
        with self.assertRaises(CalledProcessError) as failure:
            cmdx(giftp, "init", "--sub", cwd=self.superp)
        e = failure.exception

        self.assertEqual(2, e.returncode)
        self.assertEqual(usage + "42", e.err[-1])

    def test_bad_gift_refs(self):
        fwrite(pjoin(self.superp, ".gift-refs"), "- [foo/bar\n")
        cmdx(origit, "add", ".gift-refs", cwd=self.superp)
        cmdx(origit, *ident_args, "commit", "-m", "bad refs", cwd=self.superp)

        # The error goes to stderr once, and not to stdout
        _, out, err = cmdx(giftp, "reset", "-q", "HEAD", cwd=self.superp)
        self.assertEqual([], out)

        gift_lines = [line for line in err if line.startswith("GIFT: ")]
        self.assertEqual(["GIFT: can not parse .gift-refs in HEAD:"], gift_lines)

    def test_undecodable_gift_refs(self):
        refsp = pjoin(self.superp, ".gift-refs")
        with open(refsp, "wb") as f:
            f.write(b"\xff\n")
        refserr = ".gift-refs: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"

        # Each command reads .gift-refs, for a sub-repo without a git dir
        for cmds in (["init", "--sub"], ["fetch", "--sub"], ["clone", "--sub", "../wowgit@master", "wow"]):
            force_remove(pjoin(self.supergitp, "gift"))

            with self.assertRaises(CalledProcessError, msg=cmds) as failure:
                cmdx(giftp, *ident_args, *cmds, cwd=self.superp)
            err = failure.exception.err

            self.assertEqual(2, failure.exception.returncode, cmds)
            self.assertEqual(refserr, err[-1], cmds)
            self.assertEqual([], [line for line in err if "Traceback" in line], cmds)

        # The file stays as it is, for the user to fix
        with open(refsp, "rb") as f:
            content = f.read()
        self.assertEqual(b"\xff\n", content)


class TestGitSubrepo(BaseTest):

    def setUp(self):
        self.repo = pjoin(self.base, "repo")

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
        code, _, err = self._update("bar " + self.bargitp + " master\n")
        self.assertEqual(0, code, err)
        self.assertEqual("bar\n", fread(pjoin(self.repo, "bar", "bar")))

    def test_url_is_data(self):
        # ${prefix} in a url is the dir
        code, _, err = self._update("bargit " + pjoin(self.base, "testdata") + "/${prefix} master\n")
        self.assertEqual(0, code, err)
        self.assertEqual("bar\n", fread(pjoin(self.repo, "bargit", "bar")))

        # Other shell syntax in a url is not run
        self._update("dep $(touch${IFS}marker) master\n")
        self.assertFalse(os.path.exists(pjoin(self.repo, "marker")))

    def test_url_is_not_option(self):
        markerp = pjoin(self.base, "marker")
        helperp = pjoin(self.base, "helper")
        fwrite(helperp, "#!/bin/sh\ntouch " + markerp + "\nexit 1\n")
        os.chmod(helperp, 0o755)
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.repo)

        # git must not read the url as --upload-pack, which runs the helper
        code, _, _ = self._update("dep --upload-pack=" + helperp + " " + self.bargitp + "\n")

        self.assertEqual(1, code)
        self.assertFalse(os.path.exists(markerp))
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.repo))

    def test_tag_per_dir(self):
        # "." in a dir must not turn into a char that another dir has: each
        # dir is fetched into its own tag
        wowgitp = pjoin(self.base, "testdata", "wowgit")
        code, _, err = self._update("foo.bar " + self.bargitp + " master\nfoo-bar " + wowgitp + " master\n")
        self.assertEqual(0, code, err)

        paths = cmdout(origit, "ls-tree", "-r", "--name-only", "HEAD", cwd=self.repo)
        self.assertEqual(["foo-bar/wow", "foo.bar/bar"], paths)
        self.assertEqual(["bar"], cmdout(origit, "show", "HEAD:foo.bar/bar", cwd=self.repo))
        self.assertEqual(["wow"], cmdout(origit, "show", "HEAD:foo-bar/wow", cwd=self.repo))

    def test_failed_merge(self):
        head = cmd0(origit, "rev-parse", "HEAD", cwd=self.repo)
        branch_ref = cmd0(origit, "symbolic-ref", "HEAD", cwd=self.repo)

        # git can not move the branch while its lock file is there
        fwrite(pjoin(self.repo, ".git", branch_ref + ".lock"), "")
        wowgitp = pjoin(self.base, "testdata", "wowgit")
        code, _, _ = self._update("bar " + self.bargitp + " master\nwow " + wowgitp + " master\n")

        # The fetches finish in any order, and the import stops after the
        # first dir
        imported = [d for d in ("bar", "wow") if os.path.exists(pjoin(self.repo, d))]

        self.assertEqual(1, code)
        self.assertEqual(head, cmd0(origit, "rev-parse", "HEAD", cwd=self.repo))
        self.assertIn(imported, (["bar"], ["wow"]))

    def test_failed_fetch(self):
        code, _, _ = self._update("bar " + self.bargitp + " master\nnosuch " + pjoin(self.repo, "nosuch") + " master\n")
        self.assertEqual(1, code)

        # bar is not imported, and its fetched tag is removed
        self.assertFalse(os.path.exists(pjoin(self.repo, "bar")))
        self.assertEqual([], cmdout(origit, "for-each-ref", "refs/tags", cwd=self.repo))


def force_remove(fn):

    try:
        shutil.rmtree(fn)
    except FileNotFoundError:
        pass
