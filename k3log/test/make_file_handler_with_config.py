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


rm_file('/tmp/handler_change')

l = k3log.make_logger(base_dir='/tmp',
                      log_name='h',
                      log_fn='dd',
                      level='INFO',
                      fmt='%(message)s',
                      datefmt='%H%M%S'
                      )
l.handlers = []
handler = k3log.make_file_handler(log_fn='handler_change',
                                  fmt='%(message)s',
                                  datefmt='%H%M%S')
l.addHandler(handler)

l.debug('debug')
l.info('info')

cont = read_file('/tmp/handler_change').strip()

print(cont)
