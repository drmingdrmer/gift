import os
import unittest
import uuid

import k3proc
import k3ut

dd = k3ut.dd

this_base = os.path.dirname(__file__)


class TestConfLoader(unittest.TestCase):

    def test_default(self):
        defaults = dict(
            uid=None,
            gid=None,
            log_dir=None,
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

        for k, v in defaults.items():
            self._test_get_conf(k, str(v))

    def test_configured(self):
        defaults = dict(
            uid=1,
            gid=2,
            log_dir='/tmp',
            cat_stat_dir='/var/log',
            zk_acl=('a', 'b'),
            zk_auth=('digest', 'xp', '123'),
            iostat_stat_path='/tmp/ps',
            zk_hosts='127.0.0.1:21812',
            zk_lock_dir='lock/222',
            zk_node_id='123',
            zk_record_dir='rec/',
            zk_tx_dir='t/',
            zk_seq_dir='sq/',
            zk_tx_timeout=3,
            rp_cli_nwr=(4, 3, 2),
            rp_cli_ak_sk=('access', 'secret'),
            ec_block_port=6001,
            inner_ip_patterns=[123],
        )

        for k, v in defaults.items():
            self._test_get_conf(k, str(v), cwd=os.path.join(this_base, 'configured'))

    def test_lazyload(self):

        code, out, err = k3proc.command(
            'python', '-c', 'import k3confloader as cl; print(1)',
            check=True,
            cwd=os.path.join(this_base, 'lazyload'),
        )

        dd("code:", code)
        dd("out:", out)
        dd("err:", err)

        self.assertEqual('1', out.strip())

        # When reading attributes, there should be an error

        try:
            k3proc.command(
                'python', '-c', 'import k3confloader as cl; print(cl.conf.uid)',
                check=False,
                cwd=os.path.join(this_base, 'lazyload'),
            )
        except k3proc.CalledProcessError as e:
            self.assertEqual('should not be here', e.stderr.strip())
            self.assertEqual(1, e.returncode)

    def _test_get_conf(self, k, v, cwd=None):
        code, out, err = k3proc.command(
            'python', '-c', 'import k3confloader as cl; print(cl.conf.' + k + ')',
            check=True,
            cwd=cwd,
        )

        dd("k, v:", k, v)
        dd("code:", code)
        dd("out:", out)
        dd("err:", err)

        self.assertEqual(v, out.strip())
