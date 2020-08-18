import errno
import os

import k3log


def read_file(fn):
    with open(fn, 'r') as f:
        return f.read()


def rm_file(fn):
    try:
        os.unlink(fn)
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass
        else:
            raise


rm_file('/tmp/tt')

l = k3log.make_logger(base_dir=None,
                      log_name='m',
                      log_fn='tt',
                      level='INFO',
                      fmt='%(message)s',
                      datefmt='%H%M%S'
                      )

l.debug('debug')
l.info('info')

cont = read_file('/tmp/tt').strip()
print(cont)
