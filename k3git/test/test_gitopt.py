import os
import unittest

import k3ut
from k3git import GitOpt

dd = k3ut.dd

this_base = os.path.dirname(__file__)


class TestGitOpt(unittest.TestCase):

    def test_informative_opts(self):
        cases = (
                (['--version'], None),
                (['--help'], None),
                (['--html-path'], None),
                (['--info-path'], None),
                (['--man-path'], None),
                (['--exec-path'], None),
                (['--version', '--exec-path'], None),
        )

        for inp, want in cases:
            if want is None:
                want = inp[:]

            dd(inp)
            dd(want)

            o = GitOpt().parse_args(inp[:])
            for k in want:
                self.assertEqual(k, o.informative_cmds[k])

    def test_cmds(self):
        cases = (
                (['-C', 'b', '--version', 'commit', '--version', '/p'], ['commit', '--version', '/p'], ['-C', 'b']),
                (['-C', 'b', 'commit', '--version', '/p'], ['commit', '--version', '/p'], ['-C', 'b']),
        )

        for inp, wantcmd, wantargs in cases:

            dd(inp)
            dd(wantcmd)
            dd(wantargs)

            o = GitOpt().parse_args(inp[:])
            self.assertEqual(wantcmd, o.cmds)
            self.assertEqual(wantargs, o.to_args())

    def test_additional(self):

        cases = (
                (['-C', 'b', '--foo', 'commit', '--bar', '/p'],
                 ['commit', '--bar', '/p'], ['-C', 'b'], {'--foo': '--foo'}),
        )

        for inp, wantcmd, wantargs, wantadd in cases:

            dd(inp)
            dd(wantcmd)
            dd(wantargs)
            dd(wantadd)

            o = GitOpt().parse_args(inp[:], additional=['--foo'])
            self.assertEqual(wantcmd, o.cmds)
            self.assertEqual(wantargs, o.to_args())
            self.assertEqual(wantadd, o.additional)

    def test_update(self):
        o = GitOpt().parse_args(['-C', 'a'])
        o.update({'startpath': 'c'})

        self.assertEqual(['-C', 'c'], o.to_args())

    def test_clone(self):
        o = GitOpt().parse_args(['-C', 'a', '--version', '--bar'], additional={'--bar': True})

        p = o.clone()
        p.update({'startpath': 'c'})

        del o.informative_cmds['--version']
        del o.additional['--bar']

        self.assertEqual(['-C', 'a'], o.to_args())
        self.assertEqual(['-C', 'c'], p.to_args())
        self.assertEqual('--version', p.informative_cmds['--version'])
        self.assertEqual('--bar', p.additional['--bar'])

    def test_to_args(self):

        cases = (
                (['-C', 'a', '-C', 'b'], None),
                (['-c', 'a=b', '-C', 'b'], ['-C', 'b', '-c', 'a=b', ]),
                (['--exec-path=/d'], None),
                (['-p'], ['-p']),
                (['--paginate'], ['-p']),
                (['--no-pager'], None),
                (['--no-pager', '-p'], ['-p']),
                (['--no-replace-objects'], None),
                (['--bare'], None),
                (['--git-dir=a'], None),
                (['--work-tree=a'], None),
                (['--namespace=a'], None),
                (['--super-prefix=a'], None),
        )
        for inp, want in cases:
            if want is None:
                want = inp[:]

            dd(inp)
            dd(want)

            o = GitOpt().parse_args(inp[:])
            rst = o.to_args()
            self.assertEqual(want, rst)
