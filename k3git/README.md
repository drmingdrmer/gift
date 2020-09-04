# k3git

[![Build Status](https://travis-ci.com/pykit3/k3git.svg?branch=master)](https://travis-ci.com/pykit3/k3git)
[![Documentation Status](https://readthedocs.org/projects/k3git/badge/?version=stable)](https://k3git.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3git)](https://pypi.org/project/k3git)

wrapper of git command-line

k3git is a component of [pykit3] project: a python3 toolkit set.


# Install

```
pip install k3git
```

# Synopsis

```python
>>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).cmds
['fetch', 'origin']
>>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).to_args()
['--git-dir=/foo']
```

#   Author

Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>

#   Copyright and License

The MIT License (MIT)

Copyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>


[pykit3]: https://github.com/pykit3