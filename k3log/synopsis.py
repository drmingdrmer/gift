import k3log
# make a file logger in one line
logger = k3log.make_logger('/tmp', level='INFO', fmt='%(message)s',
                           datefmt="%H:%M:%S")
logger.info('foo')

logger.stack_str(fmt="{fn}:{ln} in {func}\n  {statement}", sep="\n")
# runpy.py:174 in _run_module_as_main
#   "__main__", fname, loader, pkg_name)
# runpy.py:72 in _run_code
#   exec code in run_globals
# ...
# test_logutil.py:82 in test_deprecate
#   k3log.deprecate()
#   'foo', fmt='{fn}:{ln} in {func}\n  {statement}', sep='\n')
