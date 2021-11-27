#!/usr/bin/env python
# coding: utf-8

import logging
import os

from k3handy import cmdf
from k3handy import pabs
from k3str import to_utf8

logger = logging.getLogger(__name__)


class Git(object):

    def __init__(self, opt, gitpath=None, gitdir=None, working_dir=None, cwd=None, ctxmsg=None):
        self.opt = opt.clone()
        # gitdir and working_dir is specified and do not consider '-C' option
        if gitdir is not None:
            self.opt.opt['git_dir'] = pabs(gitdir)
        if working_dir is not None:
            self.opt.opt['work_tree'] = pabs(working_dir)

        self.cwd = cwd

        self.gitpath = gitpath or "git"
        self.ctxmsg = ctxmsg

    # high level API

    def checkout(self, branch, flag='x'):
        return self.cmdf("checkout", branch, flag=flag)

    def fetch(self, name, flag=''):
        return self.cmdf("fetch", name, flag=flag)

    def reset_to_commit(self, mode, target=None, flag='x'):
        """
        mode is one of `soft`, `mixed`, `hard`, `merge`, `keep`.
        """
        if target is None:
            target = 'HEAD'

        return self.cmdf('reset', '--' + mode, target, flag=flag)

    # worktree

    def worktree_is_clean(self, flag=''):
        """
        Return whether worktree is clean
        """
        # git bug: 
        # Without running 'git status' first, "diff-index" in our test does not
        # pass
        self.cmdf("status", flag='')
        code, _out, _err = self.cmdf("diff-index", "--quiet", "HEAD", "--", flag=flag)
        return code == 0

    # branch

    def branch_default_remote(self, branch, flag=''):
        """
        Returns the default remote name of a branch.
        """
        return self.cmdf('config', '--get',
                         'branch.{}.remote'.format(branch),
                         flag=flag + 'n0')

    def branch_default_upstream(self, branch, flag=''):
        """
        Returns the default upstream name of a branch,
        i.e., the default upstream for master is origin/master.
        """
        return self.cmdf('rev-parse',
                         '--abbrev-ref',
                         '--symbolic-full-name',
                         branch +'@{upstream}', 
                         flag=flag + 'n0')

    def branch_set(self, branch, rev, flag='x'):
        """
        Set branch ref to specified ``rev``.
        """

        self.cmdf('update-ref', 'refs/heads/{}'.format(branch), rev, flag=flag)

    def branch_common_base(self, branch, other, flag=''):
        """
        Find the common base of two branches
        """

        return self.cmdf('merge-base', branch, other, flag=flag+'0')

    def branch_divergency(self, branch, upstream=None, flag=''):
        """
        Return the divergency between a branch and another.
        If upstream is None, the default upstream is used.

        Return: (list, list) commits from common base to branch and commits from common base to upstream.
        """

        if upstream is None:
            upstream = self.branch_default_upstream(branch, flag='x')

        base = self.branch_common_base(branch, upstream, flag='x')

        b_logs = self.cmdf("log", "--format=%H", base + '..' + branch, flag='xo')
        u_logs = self.cmdf("log", "--format=%H", base + '..' + upstream, flag='xo')

        return (base, b_logs, u_logs)

    # head

    def head_branch(self, flag=''):
        """
        Returns the branch HEAD pointing to.
        """
        return self.cmdf('symbolic-ref', '--short', 'HEAD', flag=flag + 'n0')

    # remote

    def remote_get(self, name, flag=''):
        # TODO: by default all func should raise
        return self.cmdf("remote", "get-url", name, flag=flag + 'n0')

    def remote_add(self, name, url, flag='x', **options):
        self.cmdf("remote", "add", name, url, **options, flag=flag)

    # blob

    def blob_new(self, f, flag=''):
        return self.cmdf("hash-object", "-w", f, flag=flag + 'n0')

    #  tree

    def tree_of(self, commit, flag=''):
        return self.cmdf("rev-parse", commit + "^{tree}", flag=flag + 'n0')

    def tree_commit(self, treeish, commit_message, parent_commits, flag='x'):

        """
        Create a commit of content ``treeish``, ``commit_message``, and add all
        commit hashes in ``parent_commits`` as its parents.
        """

        parent_args = []
        for c in parent_commits:
            parent_args.extend(['-p', c])

        return self.cmdf('commit-tree', treeish, *parent_args,
                         input=commit_message, flag=flag + 'n0')

    def tree_items(self, treeish, name_only=False, with_size=False, flag='x'):
        args = []
        if name_only:
            args.append("--name-only")

        if with_size:
            args.append("--long")
        return self.cmdf("ls-tree", treeish, *args, flag=flag + 'no')

    def tree_add_obj(self, cur_tree, path, treeish):

        sep = os.path.sep

        itms = self.tree_items(cur_tree)

        if sep not in path:
            return self.tree_new_replace(itms, path, treeish, flag='x')

        # a/b/c -> a, b/c
        p0, left = path.split(sep, 1)
        p0item = self.tree_find_item(cur_tree, fn=p0, typ="tree")

        if p0item is None:

            newsubtree = treeish
            for p in reversed(left.split(sep)):
                newsubtree = self.tree_new_replace([], p, newsubtree, flag='x')
        else:

            subtree = p0item["object"]
            newsubtree = self.tree_add_obj(subtree, left, treeish)

        return self.tree_new_replace(itms, p0, newsubtree, flag='x')

    def tree_find_item(self, treeish, fn=None, typ=None):
        for itm in self.tree_items(treeish):
            itm = self.treeitem_parse(itm)
            if fn is not None and itm["fn"] != fn:
                continue
            if typ is not None and itm["type"] != typ:
                continue

            return itm
        return None

    def treeitem_parse(self, line):

        # git-ls-tree output:
        #     <mode> SP <type> SP <object> TAB <file>
        # This output format is compatible with what --index-info --stdin of git update-index expects.
        # When the -l option is used, format changes to
        #     <mode> SP <type> SP <object> SP <object size> TAB <file>
        # E.g.:
        # 100644 blob a668431ae444a5b68953dc61b4b3c30e066535a2    imsuperman
        # 040000 tree a668431ae444a5b68953dc61b4b3c30e066535a2    foo

        p, fn = line.split("\t", 1)

        elts = p.split()
        rst = {
            "mode": elts[0],
            "type": elts[1],
            "object": elts[2],
            "fn": fn,
        }
        if len(elts) == 4:
            rst["size"] = elts[3]

        return rst

    def tree_new(self, itms, flag='x'):

        treeish = self.cmdf("mktree", input="\n".join(itms), flag=flag + 'n0')
        return treeish

    def tree_new_replace(self, itms, name, obj, mode=None, flag='x'):

        new_items = self.treeitems_replace_item(itms, name, obj, mode=mode)

        new_treeish = self.cmdf("mktree", input="\n".join(new_items), flag=flag + 'n0')
        return new_treeish

    def treeitems_replace_item(self, itms, name, obj, mode=None):

        new_items = [x for x in itms
                     if self.treeitem_parse(x)["fn"] != name]

        if obj is not None:
            itm = self.treeitem_new(name, obj, mode=mode)
            new_items.append(itm)

        return new_items

    # treeitem

    def treeitem_new(self, name, obj, mode=None):

        typ = self.obj_type(obj, flag='x')
        item_fmt = "{mode} {typ} {object}\t{name}"

        if typ == 'tree':
            mod = "040000"
        else:
            if mode is None:
                mod = "100644"
            else:
                mod = mode

        itm = item_fmt.format(mode=mod,
                              typ=typ,
                              object=obj,
                              name=name
                              )
        return itm

    # rev

    def rev_of(self, name, flag=''):
        """
        Get the revision(sha256) of an object.

        Args:

            name(str): could be short hash, full length hash, ref name or branch.

            flag(str): flag='x' to raise if return code is not 0. flag='' to return None.

        Returns:
            str: sha256 in lower-case hex. If no such object is found, it returns None.
        """
        return self.cmdf("rev-parse", "--verify", "--quiet", name, flag=flag + 'n0')

    def obj_type(self, obj, flag=''):
        return self.cmdf("cat-file", "-t", obj, flag=flag + 'n0')

    # wrapper of cli

    def _opt(self, **kwargs):
        opt = {}
        if self.cwd is not None:
            opt["cwd"] = self.cwd
        opt.update(kwargs)
        return opt

    def _args(self):
        return self.opt.to_args()

    def cmdf(self, *args, flag='', **kwargs):
        return cmdf(self.gitpath, *self._args(), *args, flag=flag, **self._opt(**kwargs))

    def out(self, fd, *msg):

        if self.ctxmsg is not None:
            os.write(fd, to_utf8(self.ctxmsg) + b": ")

        for (i, m) in enumerate(msg):
            os.write(fd, to_utf8(m))
            if i != len(msg) - 1:
                os.write(fd, b" ")
        os.write(fd, b"\n")
