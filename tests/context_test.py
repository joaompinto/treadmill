"""Unit test for fs - configuring unshared chroot.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

from ldap3.core import exceptions as ldap_exceptions
import mock

import treadmill
from treadmill import context


class ContextTest(unittest.TestCase):
    """Tests for teadmill.context."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch('treadmill.admin.Admin.connect', mock.Mock())
    @mock.patch('treadmill.admin.Cell.get', mock.Mock())
    @mock.patch('treadmill.dnsutils.query', mock.Mock(return_value=[]))
    def test_ldap_resolve(self):
        """Test lazy resolve logic."""
        # missing search base.
        # TODO: renable this test once we can firgure out why ctx0.ldap.conn is
        # mocked when running with nosetest and Train
        # ctx0 = context.Context()
        # self.assertRaises(context.ContextError, ctx0.resolve, 'somecell')

        # Missing ldap url
        ctx1 = context.Context()
        ctx1.ldap_suffix = 'dc=test'
        # TODO: renable this test once we can firgure out why ctx0.ldap.conn is
        # mocked when running with nosetest and Train
        # self.assertRaises(context.ContextError, ctx1.resolve, 'somecell')

        # Cell not defined in LDAP.
        ctx2 = context.Context()
        ctx2.cell = 'somecell'
        ctx2.ldap_suffix = 'dc=test'
        ctx2.ldap.url = 'ldap://foo:1234'
        treadmill.admin.Cell.get.side_effect =\
            ldap_exceptions.LDAPNoSuchObjectResult

        self.assertIsNone(ctx2.get('zk_url'))

        self.assertRaises(context.ContextError, lambda: ctx2.zk.conn)

        # Cell defined in LDAP
        ctx3 = context.Context()
        ctx2.cell = 'somecell'
        ctx3.ldap_suffix = 'dc=test'
        ctx3.ldap.url = 'ldap://foo:1234'

        treadmill.admin.Cell.get.side_effect = None
        treadmill.admin.Cell.get.return_value = {
            'username': 'tmtest',
            'masters': [
                {'hostname': 'xxx', 'zk-client-port': 123},
                {'hostname': 'yyy', 'zk-client-port': 345},
            ]
        }
        ctx3.cell = 'somecell'
        ctx3.get('zk_url')
        self.assertEqual(
            'zookeeper://tmtest@xxx:123,yyy:345/treadmill/somecell',
            ctx3.zk.url
        )

    @mock.patch('treadmill.admin.Admin.connect', mock.Mock())
    @mock.patch('treadmill.dnsutils.txt', mock.Mock(return_value=[]))
    @mock.patch('treadmill.dnsutils.srv', mock.Mock(return_value=[]))
    @mock.patch('treadmill.zkutils.connect', mock.Mock())
    def test_dns_resolve(self):
        """Test lazy resolve logic."""
        # missing search base.
        # TODO: renable this test once we can firgure out why ctx0.ldap.conn is
        # mocked when running with nosetest and Train
        # ctx0 = context.Context()
        # self.assertRaises(context.ContextError, ctx0.resolve, 'somecell')

        ctx1 = context.Context()
        ctx1.ldap_suffix = 'dc=test'
        ctx1.dns_domain = 'x'
        ctx1.cell = 'somecell'

        treadmill.dnsutils.txt.return_value = [
            'zookeeper://tmtest@xxx:123,yyy:345/treadmill/somecell',
        ]
        treadmill.dnsutils.srv.return_value = [
            ('ldaphost1', 1234, 10, 10),
            ('ldaphost2', 2345, 10, 10)
        ]
        ctx1.get('zk_url')
        self.assertEqual(
            'zookeeper://tmtest@xxx:123,yyy:345/treadmill/somecell',
            ctx1.zk.url
        )
        self.assertEqual(
            'ldap://ldaphost1:1234,ldap://ldaphost2:2345',
            ctx1.ldap.url
        )

        # Test automatic resolve invocation
        ctx2 = context.Context()
        ctx2.ldap_suffix = 'dc=test'
        ctx2.cell = 'somecell'
        ctx2.dns_domain = 'x'
        # Disable E1102: not callable
        ctx2.zk.conn()  # pylint: disable=E1102
        self.assertEqual(
            'zookeeper://tmtest@xxx:123,yyy:345/treadmill/somecell',
            ctx2.zk.url
        )

    @mock.patch('treadmill.dnsutils.srv', mock.Mock(return_value=[]))
    def test_api_resolve(self):
        """Tests resolving API from DNS srv records."""
        treadmill.dnsutils.srv.return_value = [('xxx', 123, 1, 2),
                                               ('yyy', 234, 3, 4)]

        ctx = context.Context()
        ctx.dns_domain = 'a'
        ctx.profile['api_scope'] = ['ny.campus', 'na.region']
        ctx.cell = 'b'
        self.assertEqual(
            set(['http://xxx:123', 'http://yyy:234']),
            set(ctx.cell_api())
        )
        treadmill.dnsutils.srv.assert_called_with(
            '_http._tcp.cellapi.b.cell.a', mock.ANY
        )

        self.assertEqual(['x:8080'], ctx.cell_api('x:8080'))

        ctx.cell = None
        self.assertRaises(context.ContextError, ctx.cell_api)
        self.assertEqual(['x:8080'], ctx.cell_api('x:8080'))

        ctx.cell = 'a'
        ctx.dns_domain = None
        self.assertRaises(context.ContextError, ctx.cell_api)
        self.assertEqual(['x:8080'], ctx.cell_api('x:8080'))

        ctx.dns_domain = 'a.com'
        treadmill.dnsutils.srv.return_value = []
        self.assertRaises(context.ContextError, ctx.admin_api)
        treadmill.dnsutils.srv.assert_has_calls([
            mock.call('_http._tcp.adminapi.ny.campus.a.com', mock.ANY),
            mock.call('_http._tcp.adminapi.na.region.a.com', mock.ANY),
        ])


if __name__ == '__main__':
    unittest.main()
