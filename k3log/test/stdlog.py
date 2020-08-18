import logging

import k3log

logger = k3log.make_logger('/tmp', log_fn='stdlog', level='INFO',
                           fmt='message')


k3log.add_std_handler(logger, 'stdout', fmt='message', level=logging.ERROR)
logger.debug('debug')
logger.info('stdlog')
logger.error('error')
