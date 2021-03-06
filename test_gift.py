#!/usr/bin/env python
# coding: utf-8


# TODO test: commit --sub with dirty work dir
# TODO commit --sub add history to commit log
import imp
import os
import shutil
import tempfile
import unittest

from k3fs import fread
from k3fs import fwrite
from k3git import GitOpt
from k3handy import cmd0
from k3handy import cmdout
from k3handy import cmdtty
from k3handy import cmdx
from k3handy import dd
from k3handy import pjoin

gift = imp.load_source('gift', './gift')

CalledProcessError = gift.CalledProcessError

Git = gift.Git
Gift = gift.Gift


# root of this repo
this_base = os.path.dirname(__file__)

giftp = pjoin(this_base, "gift")
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
    cmdx(origit, "clean", "-dxf", cwd=this_base)


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
            'refhead': 'refs/gift/sub/foo/bar',
            'sub_gitdir': 'gift/subdir/foo/bar',
            'upstream': {'branch': 'master', 'name': 'origin', 'url': '../bargit'}
        }, sb)


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
        self.assertEqual('gift version 0.1.0', out[0])
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
                'GIFT: path/to/bar: add remote: origin ../bargit',
                'GIFT: path/to/bar: fetch origin ../bargit',
                "From ../bargit",
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

    def test_fetch_sub(self):

        cmdx(giftp, "init", "--sub", cwd=superp)

        headhash = self._add_commit_to_bar_from_other_clone()

        # we should fetch and got the latest commit.

        cmdx(giftp, "fetch", "--sub", cwd=superp)

        fetched_hash = cmd0(giftp, "rev-parse", "origin/master", cwd=subbarp)

        self.assertEqual(headhash, fetched_hash)

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
        self.assertNotEqual(head_of_bar, head2)

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

        self.assertNotEqual(head_of_bar, head_of_bar_after_checkout)


def force_remove(fn):

    try:
        shutil.rmtree(fn)
    except BaseException:
        pass

    try:
        os.unlink(fn)
    except BaseException:
        pass
