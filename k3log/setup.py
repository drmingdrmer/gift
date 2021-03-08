# DO NOT EDIT!!! built with `python _building/build_setup.py`
import setuptools
setuptools.setup(
    name="k3log",
    packages=["k3log"],
    version="0.1.3",
    license='MIT',
    description='k3log is a collection of log utilities.',
    long_description='# k3log\n\n[![Build Status](https://travis-ci.com/pykit3/k3log.svg?branch=master)](https://travis-ci.com/pykit3/k3log)\n![Python package](https://github.com/pykit3/k3log/workflows/Python%20package/badge.svg)\n[![Documentation Status](https://readthedocs.org/projects/k3log/badge/?version=stable)](https://k3log.readthedocs.io/en/stable/?badge=stable)\n[![Package](https://img.shields.io/pypi/pyversions/k3log)](https://pypi.org/project/k3log)\n\nk3log is a collection of log utilities.\n\nk3log is a component of [pykit3] project: a python3 toolkit set.\n\n\nk3log is a collection of log utilities for logging.\n\n\n\n# Install\n\n```\npip install k3log\n```\n\n# Synopsis\n\n```python\n\n# make a file logger in one line\nlogger = pk3logutil.make_logger(\'/tmp\', level=\'INFO\', fmt=\'%(message)s\',\n                                datefmt="%H:%M:%S")\nlogger.info(\'foo\')\n\nlogger.stack_str(fmt="{fn}:{ln} in {func}\\n  {statement}", sep="\\n")\n# runpy.py:174 in _run_module_as_main\n#   "__main__", fname, loader, pkg_name)\n# runpy.py:72 in _run_code\n#   exec code in run_globals\n# ...\n# test_logutil.py:82 in test_deprecate\n#   pk3logutil.deprecate()\n#   \'foo\', fmt=\'{fn}:{ln} in {func}\\n  {statement}\', sep=\'\\n\')\n\n```\n\n#   Author\n\nZhang Yanpo (张炎泼) <drdr.xp@gmail.com>\n\n#   Copyright and License\n\nThe MIT License (MIT)\n\nCopyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>\n\n\n[pykit3]: https://github.com/pykit3',
    long_description_content_type="text/markdown",
    author='Zhang Yanpo',
    author_email='drdr.xp@gmail.com',
    url='https://github.com/pykit3/k3log',
    keywords=['logging', 'stack'],
    python_requires='>=3.0',

    install_requires=['semantic_version~=2.8.5', 'jinja2~=2.11.2', 'PyYAML~=5.3.1', 'sphinx~=3.3.1', 'numpy~=1.16.3', 'k3ut~=0.1.7', 'k3proc~=0.2.3', 'k3confloader~=0.1.0'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
    ] + ['Programming Language :: Python :: 3.6', 'Programming Language :: Python :: 3.7', 'Programming Language :: Python :: 3.8', 'Programming Language :: Python :: Implementation :: PyPy'],
)
