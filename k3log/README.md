# k3log

[![Build Status](https://travis-ci.com/pykit3/k3log.svg?branch=master)](https://travis-ci.com/pykit3/k3log)
[![Documentation Status](https://readthedocs.org/projects/k3log/badge/?version=stable)](https://k3log.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3log)](https://pypi.org/project/k3log)

k3log is a collection of log utilities.

k3log is a component of [pykit3] project: a python3 toolkit set.


# Install

```
pip install k3log
```

# Synopsis

```python

# make a file logger in one line
logger = pk3logutil.make_logger('/tmp', level='INFO', fmt='%(message)s',
                                datefmt="%H:%M:%S")
logger.info('foo')

logger.stack_str(fmt="{fn}:{ln} in {func}\n  {statement}", sep="\n")
# runpy.py:174 in _run_module_as_main
#   "__main__", fname, loader, pkg_name)
# runpy.py:72 in _run_code
#   exec code in run_globals
# ...
# test_logutil.py:82 in test_deprecate
#   pk3logutil.deprecate()
#   'foo', fmt='{fn}:{ln} in {func}\n  {statement}', sep='\n')

```

#   Author

Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>

#   Copyright and License

The MIT License (MIT)

Copyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>


[pykit3]: https://github.com/pykit3