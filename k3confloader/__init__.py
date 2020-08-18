#!/usr/bin/env python
# coding: utf-8

"""
k3confloader loads conf for other pykit3 modules.
k3confloader tries to load a python file `k3conf.py` and expected it contains configuration.

Usage:

Setup config::

    echo 'uid=3' > k3conf.py

Then::

    import k3confloader
    print(k3confloader.conf.uid)
    3
"""

import copy
import logging
import uuid

logger = logging.getLogger(__name__)


__name__ = 'k3confloader'
__version__ = '0.1.0'


def try_load():
    """
    Try to load config from a top-level module k3conf
    """
    try:
        import k3conf
    except ImportError:
        k3conf = object()
        logger.info('k3conf not found by "import k3conf".'
                    ' Using default config.'
                    ' You can create file "pykitconf.py" to define default config for pykit.')
    return k3conf


class ConfGetter(object):
    """
    This is a lazy loader that tries to import `k3conf.py` when configure
    attributes are read.

    If an attribute is not set in `k3conf.py`, a default value is used.

    Attributes:

        uid(int):              the user  id to assign when creating file/dir. Default: None.
        gid(int):              the group id to assign when creating file/dir. Default: None.
        log_dir(str):          the log dir. Default: '/tmp'.
        cat_stat_dir(str):     the dir to store offset of an unfinished `cat` operation. Default: None.
        zk_acl(tuples):        default zookeeper acl when creating a node in form of: (('xp', '123', 'cdrwa'), ('foo', 'bar', 'rw')). Default: None.
        zk_auth(tuple):        zookeeper auth info when connecting zk in form of: ('digest', 'xp', '123'). Default: None.
        iostat_stat_path(str): a path to file to store incremental stat collection. Default: '/tmp/pykit-iostat'.
        zk_hosts(str):         default zookeeper host to connect, seperated by comma. Default: '127.0.0.1:21811'.
        zk_lock_dir(str):      default zk-dir path to impl a distributed locking. Default: 'lock/'.
        zk_node_id(str):       a node id generated from MAC. Default: '%012x' % uuid.getnode().
        zk_record_dir(str):    default zk-dir to store records of a distributed transaction. Default: 'record/'.
        zk_tx_dir(str):        default zk-dir to store tx info of a distributed transaction. Default: 'tx/'.
        zk_seq_dir(str):       default zk-dir for generating mono incremental seq number.    Default: 'seq/'.
        zk_tx_timeout(str):    default timeout in second for a zk based distributed transaction. Default: 365 * 24 * 3600.
        rp_cli_nwr(tuple):     default NWR(n, write, read) config of majority read/write for redis proxy. Default: (3, 2, 2).
        rp_cli_ak_sk(tuple):   default access key and secret key to auth access to redis proxy. Default: ('access_key', 'secret_key').
        ec_block_port(int):    default base tcp-port for EC block server. Default: 6000. Deprecated.
        inner_ip_patterns(str):default inner-network address regexp. Compatible with both python regexp and lua pattern. Default:  ['^172[.]1[6-9].*', '^172[.]2[0-9].*', '^172[.]3[0-1].*', '^10[.].*', '^192[.]168[.].*'].


    """

    defaults = dict(
        uid=None,
        gid=None,
        log_dir='/tmp',
        cat_stat_dir=None,
        zk_acl=None,              # (('xp', '123', 'cdrwa'), ('foo', 'bar', 'rw'))
        zk_auth=None,              # ('digest', 'xp', '123')
        iostat_stat_path='/tmp/pykit-iostat',
        zk_hosts='127.0.0.1:21811',
        zk_lock_dir='lock/',
        zk_node_id='%012x' % uuid.getnode(),
        zk_record_dir='record/',
        zk_tx_dir='tx/',
        zk_seq_dir='seq/',
        zk_tx_timeout=365 * 24 * 3600,
        rp_cli_nwr=(3, 2, 2),
        rp_cli_ak_sk=('access_key', 'secret_key'),
        ec_block_port=6000,
        inner_ip_patterns=['^172[.]1[6-9].*', '^172[.]2[0-9].*', '^172[.]3[0-1].*', '^10[.].*', '^192[.]168[.].*'],
    )

    def __init__(self):
        self.loaded = None

    def __getattr__(self, k):

        if self.loaded is None:
            self.loaded = try_load()

        # TODO key path
        df = self.defaults.get(k)
        v = getattr(self.loaded, k, df)
        v = copy.deepcopy(v)
        return v


conf = ConfGetter()
