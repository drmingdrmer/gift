# DO NOT EDIT!!! built with `python _building/build_setup.py`
import setuptools
setuptools.setup(
    name="k3git",
    packages=["k3git"],
    version="0.1.10",
    license='MIT',
    description='wrapper of git command-line',
    long_description="# k3git\n\n[![Build Status](https://travis-ci.com/pykit3/k3git.svg?branch=master)](https://travis-ci.com/pykit3/k3git)\n![Python package](https://github.com/pykit3/k3git/workflows/Python%20package/badge.svg)\n[![Documentation Status](https://readthedocs.org/projects/k3git/badge/?version=stable)](https://k3git.readthedocs.io/en/stable/?badge=stable)\n[![Package](https://img.shields.io/pypi/pyversions/k3git)](https://pypi.org/project/k3git)\n\nwrapper of git command-line\n\nk3git is a component of [pykit3] project: a python3 toolkit set.\n\n\nk3git is wrapper of git command-line.\n\nTo parse a git command ``git --git-dir=/foo fetch origin``:\n\n    >>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).cmds\n    ['fetch', 'origin']\n\n    >>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).to_args()\n    ['--git-dir=/foo']\n\n\n\n\n# Install\n\n```\npip install k3git\n```\n\n# Synopsis\n\n```python\n>>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).cmds\n['fetch', 'origin']\n>>> GitOpt().parse_args(['--git-dir=/foo', 'fetch', 'origin']).to_args()\n['--git-dir=/foo']\n```\n\n#   Author\n\nZhang Yanpo (张炎泼) <drdr.xp@gmail.com>\n\n#   Copyright and License\n\nThe MIT License (MIT)\n\nCopyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>\n\n\n[pykit3]: https://github.com/pykit3",
    long_description_content_type="text/markdown",
    author='Zhang Yanpo',
    author_email='drdr.xp@gmail.com',
    url='https://github.com/pykit3/k3git',
    keywords=['git', 'cli', 'commandline'],
    python_requires='>=3.0',

    install_requires=['k3str<0.2,>=v0.1.1', 'k3ut>=0.1.7,<0.2', 'k3handy>=0.1.4,<0.2', 'k3fs<0.2,>=0.1.5'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
    ] + ['Programming Language :: Python :: 3.6', 'Programming Language :: Python :: 3.7', 'Programming Language :: Python :: 3.8', 'Programming Language :: Python :: Implementation :: PyPy'],
)
