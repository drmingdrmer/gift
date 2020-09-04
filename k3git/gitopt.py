#!/usr/bin/env python
# coding: utf-8

import copy
import logging

logger = logging.getLogger(__name__)


class GitOpt(object):
    """
    GitOpt parses and builds git command line arguments.

    Attributes:

        cmds: parsed command, e.g. the cmds of parsed ``git --git-dir=/foo fetch origin`` is ``['fetch', 'origin']``.

        opt: parsed options.

        informative_cmds: defines the git options that is a query-like command,
            such as ``--version`` or ``--help``.

        additional: GitOpt is able to parse user defined options::

            o = GitOpt().parse_args(['--foo', 'fetch'], additional=['--foo'])
            o.additional
            # {'--foo': '--foo'}
    """

    # informative options just query for some info instead of doing anything.
    informative_opts = (
        '--version',
        '--help',
        '--html-path',
        '--info-path',
        '--man-path',
        '--exec-path',
    )

    def __init__(self):
        self.opt = {
            "startpath": [],
            "confkv": [],
            "paging": None,
            "no_replace_objects": False,
            "bare": False,
            "git_dir": None,
            "work_tree": None,
            "namespace": None,
            "super_prefix": None,
            "exec_path": None,
        }
        self.informative_cmds = {}
        self.additional = {}

        self.cmds = []

    def update(self, d):
        """
        update ``opt`` with a dictionary ``d``.

        Returns:
            self
        """
        for k, v in d.items():
            self.opt[k] = v
        return self

    def clone(self):
        """
        clone a GitOpt object so that the returned object share nothing with the original.

        Returns:
            GitOpt: a same and standalone object.
        """
        o = GitOpt()
        o.opt = copy.deepcopy(self.opt)
        o.informative_cmds = copy.deepcopy(self.informative_cmds)
        o.additional = copy.deepcopy(self.additional)
        return o

    def parse_args(self, args, additional=None):
        """
        Parse a command line input(without the "git").
        Additional user defined arguments can be specified.

        Returns:
            self
        """
        while len(args) > 0:
            arg = args.pop(0)

            if arg in self.informative_opts:
                self.informative_cmds[arg] = arg
                continue

            if arg == '-C':
                self.opt["startpath"].append(args.pop(0))
                continue
            if arg == '-c':
                self.opt["confkv"].append(args.pop(0))
                continue
            if arg.startswith('--exec-path='):
                self.opt["exec_path"] = arg.split('=', 1)[1]
                continue
            if arg in ('-p', '--paginate'):
                self.opt["paging"] = True
                continue
            if arg == '--no-pager':
                self.opt["paging"] = False
                continue

            if arg == '--no-replace-objects':
                # TODO
                self.opt["no_replace_objects"] = True
                continue

            if arg == '--bare':
                # TODO
                self.opt["bare"] = True
                continue

            if arg.startswith('--git-dir='):
                self.opt["git_dir"] = arg.split('=', 1)[1]
                continue

            if arg.startswith('--work-tree='):
                self.opt["work_tree"] = arg.split('=', 1)[1]
                continue

            if arg.startswith('--namespace='):
                # TODO
                self.opt["namespace"] = arg.split('=', 1)[1]
                continue
            if arg.startswith('--super-prefix='):
                # TODO
                self.opt["super_prefix"] = arg.split('=', 1)[1]
                continue

            if additional is not None:
                if arg in additional:
                    self.additional[arg] = arg
                    continue

            # no match, push back
            self.cmds = [arg] + args
            break

        return self

    def to_args(self):
        """
        Build git command line argument.
        E.g.::

            o = GitOpt().parse_args(['--git-dir=/foo', 'fetch'])
            o.opt['work_tree'] = '/bar'

            o.to_args() # ['--git-dir=/foo', '--work-tree=/bar']
            o.cmds      # ['fetch']

        Returns:
            list: of str that can be used in commandline.
        """
        o = self.opt
        rst = []
        for p in o['startpath']:
            rst.append('-C')
            rst.append(p)

        for kv in o['confkv']:
            rst.append('-c')
            rst.append(kv)

        if o['exec_path'] is not None:
            rst.append('--exec-path=' + o['exec_path'])

        if o['paging'] is True:
            rst.append('-p')

        if o['paging'] is False:
            rst.append('--no-pager')

        if o['no_replace_objects'] is True:
            rst.append('--no-replace-objects')

        if o['bare'] is True:
            rst.append('--bare')

        if o['git_dir'] is not None:
            rst.append('--git-dir=' + o['git_dir'])

        if o['work_tree'] is not None:
            rst.append('--work-tree=' + o['work_tree'])

        if o['namespace'] is not None:
            rst.append('--namespace=' + o['namespace'])

        if o['super_prefix'] is not None:
            rst.append('--super-prefix=' + o['super_prefix'])

        return rst
