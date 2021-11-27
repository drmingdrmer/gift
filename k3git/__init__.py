"""
k3git is wrapper of git command-line.

To parse a git command ``git --git-dir=/foo fetch origin``:

    >>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).cmds
    ['fetch', 'origin']

    >>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).to_args()
    ['--git-dir=/foo']

"""

__version__ = "0.1.10"
__name__ = "k3git"

from .gitopt import GitOpt
from .giturl import GitUrl
from .git_wrapper import Git

__all__ = [
    'Git',
    'GitOpt',
]
