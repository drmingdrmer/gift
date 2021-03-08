#!/usr/bin/env python
# coding: utf-8

import os
import logging


from k3str import to_utf8
from k3handy.path import pabs

from k3handy.cmd import cmdf

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
        self.cmdf("checkout", branch, flag=flag)

    def fetch(self, name, flag=''):
        self.cmdf("fetch", name, flag=flag)

    # remote

    def remote_get(self, name, flag=''):
        return self.cmdf("remote", "get-url", name, flag=flag + 'n0')

    def remote_add(self, name, url, flag='x', **options):
        self.cmdf("remote", "add", name, url, **options, flag=flag)

    # blob

    def blob_new(self, f, flag=''):
        return self.cmdf("hash-object", "-w", f, flag=flag + 'n0')

    #  tree

    def tree_of(self, commit, flag=''):
        return self.cmdf("rev-parse", commit + "^{tree}", flag=flag + 'n0')

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
            return self.tree_new(itms, path, treeish, flag='x')

        # a/b/c -> a, b/c
        p0, left = path.split(sep, 1)
        p0item = self.tree_find_item(cur_tree, fn=p0, typ="tree")

        if p0item is None:

            newsubtree = treeish
            for p in reversed(left.split(sep)):
                newsubtree = self.tree_new([], p, newsubtree, flag='x')
        else:

            subtree = p0item["object"]
            newsubtree = self.tree_add_obj(subtree, left, treeish)

        return self.tree_new(itms, p0, newsubtree, flag='x')

    def tree_find_item(self, treeish, fn=None, typ=None):
        for itm in self.tree_items(treeish):
            itm = self.parse_tree_item(itm)
            if fn is not None and itm["fn"] != fn:
                continue
            if typ is not None and itm["type"] != typ:
                continue

            return itm
        return None

    def parse_tree_item(self, line):

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

    def tree_new(self, itms, name, obj, mode=None, flag='x'):

        newitems = [x for x in itms
                    if self.parse_tree_item(x)["fn"] != name]

        itm = self.treeitem_new(name, obj, mode=mode)

        newitems.append(itm)
        new_treeish = self.cmdf("mktree", input="\n".join(newitems), flag=flag + 'n0')
        return new_treeish

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
