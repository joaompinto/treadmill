"""Unit test for treadmill.sproc.appmonitor.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import time
import unittest

import mock

# Disable W0611: Unused import
import tests.treadmill_test_skip_windows  # pylint: disable=W0611

from treadmill import restclient
from treadmill import zkutils
from treadmill.sproc import appmonitor


class AppMonitorTest(unittest.TestCase):
    """Test treadmill.sproc.appmonitor"""

    @mock.patch('time.time', mock.Mock())
    @mock.patch('treadmill.restclient.post', mock.Mock())
    @mock.patch('treadmill.restclient.delete', mock.Mock())
    def test_reevaluate(self):
        """Test state reevaluation."""
        zkclient = mock.Mock()

        state = {
            'scheduled': {
                'foo.bar': ['foo.bar#1', 'foo.bar.#2'],
                'foo.baz': ['foo.baz#3', 'foo.baz.#4'],
            },
            'monitors': {
                'foo.bar': {
                    'count': 2,
                    'available': 4,
                    'rate': 1.0,
                    'last_update': 100,
                },
                'foo.baz': {
                    'count': 2,
                    'available': 2,
                    'rate': 1.0,
                    'last_update': 100,
                },
            },
            'suspended': {},
        }

        time.time.return_value = 101

        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        self.assertFalse(restclient.post.called)

        state['scheduled']['foo.baz'].append('foo.baz#5')
        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        restclient.post.assert_called_with(
            ['/cellapi.sock'],
            '/instance/_bulk/delete', payload={'instances': ['foo.baz#3']},
            headers={'X-Treadmill-Trusted-Agent': 'monitor'}
        )

        self.assertEqual(101, state['monitors']['foo.bar']['last_update'])
        self.assertEqual(101, state['monitors']['foo.baz']['last_update'])

        # Remove instance from mock state.
        state['scheduled']['foo.baz'] = [
            elt for elt in state['scheduled']['foo.baz'] if elt != 'foo.baz#3'
        ]

        # Two missing.
        restclient.post.reset_mock()

        time.time.return_value = 102
        state['scheduled']['foo.bar'] = []
        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        self.assertEqual(102, state['monitors']['foo.bar']['last_update'])
        self.assertEqual(2.0, state['monitors']['foo.bar']['available'])

        # Instance match count, after 1 sec with rate of 1/s, available will
        # be 3.0
        restclient.post.reset_mock()

        time.time.return_value = 103
        state['scheduled']['foo.bar'] = ['foo.bar#5', 'foo.bar#6']
        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        self.assertEqual(103, state['monitors']['foo.bar']['last_update'])
        self.assertEqual(3.0, state['monitors']['foo.bar']['available'])

        # Need to create two instance, 3 available.
        restclient.post.reset_mock()

        state['scheduled']['foo.bar'] = []

        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        restclient.post.assert_called_with(
            ['/cellapi.sock'],
            '/instance/foo.bar?count=2', payload={},
            headers={'X-Treadmill-Trusted-Agent': 'monitor'}
        )
        self.assertEqual(1.0, state['monitors']['foo.bar']['available'])

        last_waited = appmonitor.reevaluate(
            '/cellapi.sock', state, zkclient, {})
        restclient.post.assert_called_with(
            ['/cellapi.sock'],
            '/instance/foo.bar?count=1', payload={},
            headers={'X-Treadmill-Trusted-Agent': 'monitor'}
        )
        self.assertEqual(0.0, state['monitors']['foo.bar']['available'])
        self.assertEqual(last_waited, {})

        # No available, create not called.
        restclient.post.reset_mock()

        state['scheduled']['foo.bar'] = []
        last_waited = appmonitor.reevaluate(
            '/cellapi.sock', state, zkclient, {})
        self.assertFalse(restclient.post.called)
        self.assertEqual(last_waited, {'foo.bar': 104})

        time.time.return_value = 104
        last_waited = appmonitor.reevaluate(
            '/cellapi.sock', state, zkclient, last_waited)
        restclient.post.assert_called_with(
            ['/cellapi.sock'],
            '/instance/foo.bar?count=1', payload={},
            headers={'X-Treadmill-Trusted-Agent': 'monitor'}
        )
        self.assertEqual(0.0, state['monitors']['foo.bar']['available'])
        self.assertEqual(last_waited, {})

    @mock.patch('time.time', mock.Mock())
    @mock.patch('treadmill.restclient.post', mock.Mock())
    @mock.patch('treadmill.zkutils.update', mock.Mock())
    def test_reevaluate_notfound(self):
        """Test state reevaluation."""
        zkclient = mock.Mock()

        state = {
            'scheduled': {
                'foo.bar': [],
            },
            'monitors': {
                'foo.bar': {
                    'count': 1,
                    'available': 0,
                    'rate': 1.0,
                    'last_update': 100,
                },
            },
            'suspended': {},
        }

        time.time.return_value = 101

        restclient.post.side_effect = restclient.NotFoundError('xxx')

        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        self.assertTrue(restclient.post.called)
        self.assertIn('foo.bar', state['suspended'])
        self.assertEqual(state['suspended']['foo.bar'], float(101 + 300))
        zkutils.update.assert_called_with(
            zkclient, '/app-monitors', {'foo.bar': float(101 + 300)}
        )

        restclient.post.reset_mock()
        time.time.return_value = 102
        appmonitor.reevaluate('/cellapi.sock', state, zkclient, {})
        self.assertFalse(restclient.post.called)
        self.assertIn('foo.bar', state['suspended'])
        # Delay did not increase
        self.assertEqual(state['suspended']['foo.bar'], float(101 + 300))

        # After time reached, call will happen, fail, and delay will be
        # extended.
        restclient.post.reset_mock()
        time.time.return_value = 500
        last_waited = appmonitor.reevaluate(
            '/cellapi.sock', state, zkclient, {})
        self.assertTrue(restclient.post.called)
        self.assertIn('foo.bar', state['suspended'])
        self.assertEqual(state['suspended']['foo.bar'], float(500 + 300))
        zkutils.update.assert_called_with(
            zkclient, '/app-monitors', {'foo.bar': float(500 + 300)}
        )
        self.assertEqual(last_waited, {'foo.bar': 800.0})

        # More time pass, and this time call will succeed - application will
        # be removed from delay dict.
        restclient.post.reset_mock()
        restclient.post.return_value = ()
        restclient.post.side_effect = None
        time.time.return_value = 500 + 300 + 1
        last_waited = appmonitor.reevaluate(
            '/cellapi.sock', state, zkclient, last_waited)
        self.assertTrue(restclient.post.called)
        self.assertNotIn('foo.bar', state['suspended'])
        zkutils.update.assert_called_with(
            zkclient, '/app-monitors', {}
        )
        self.assertEqual(last_waited, {})


if __name__ == '__main__':
    unittest.main()
