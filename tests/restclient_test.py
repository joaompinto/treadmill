"""Unit test for treadmill.restclient.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

import mock
import simplejson.scanner as sjs
import requests

from six.moves import http_client

from treadmill import restclient


class RESTClientTest(unittest.TestCase):
    """Mock test for RESTClient"""

    def setUp(self):
        """Setup common test variables"""
        pass

    @mock.patch('requests.get',
                return_value=mock.MagicMock(requests.Response))
    def test_get_ok(self, resp_mock):
        """Test treadmill.restclient.get OK (200)"""
        resp_mock.return_value.status_code = http_client.OK
        resp_mock.return_value.text = 'foo'

        resp = restclient.get('http://foo.com', '/')

        self.assertIsNotNone(resp)
        self.assertEqual(resp.text, 'foo')

    @mock.patch('requests.get',
                return_value=mock.MagicMock(requests.Response))
    def test_get_404(self, resp_mock):
        """Test treadmill.restclient.get NOT_FOUND (404)"""
        resp_mock.return_value.status_code = http_client.NOT_FOUND

        with self.assertRaises(restclient.NotFoundError):
            restclient.get('http://foo.com', '/')

    @mock.patch('requests.get',
                return_value=mock.MagicMock(requests.Response))
    def test_get_302(self, resp_mock):
        """Test treadmill.restclient.get FOUND (302)"""
        resp_mock.return_value.status_code = http_client.FOUND

        with self.assertRaises(restclient.AlreadyExistsError):
            restclient.get('http://foo.com', '/')

    @mock.patch('requests.get',
                return_value=mock.MagicMock(requests.Response))
    def test_get_424(self, resp_mock):
        """Test treadmill.restclient.get FAILED_DEPENDENCY (424)"""
        resp_mock.return_value.status_code = http_client.FAILED_DEPENDENCY
        resp_mock.return_value.json.return_value = {}

        with self.assertRaises(restclient.ValidationError):
            restclient.get('http://foo.com', '/')

    @mock.patch('requests.get',
                return_value=mock.MagicMock(requests.Response))
    def test_get_401(self, resp_mock):
        """Test treadmill.restclient.get UNAUTHORIZED (401)"""
        resp_mock.return_value.status_code = http_client.UNAUTHORIZED
        resp_mock.return_value.json.return_value = {}

        with self.assertRaises(restclient.NotAuthorizedError):
            restclient.get('http://foo.com', '/')

    @mock.patch('requests.get',
                return_value=mock.MagicMock(requests.Response))
    def test_get_bad_json(self, resp_mock):
        """Test treadmill.restclient.get bad JSON"""
        resp_mock.return_value.status_code = http_client.INTERNAL_SERVER_ERROR
        resp_mock.return_value.text = '{"bad json"'
        resp_mock.return_value.json.side_effect = sjs.JSONDecodeError(
            'Foo', '{"bad json"', 1
        )

        self.assertRaises(
            restclient.MaxRequestRetriesError,
            restclient.get, 'http://foo.com', '/', retries=1)

    @mock.patch('time.sleep', mock.Mock())
    @mock.patch('treadmill.restclient._handle_error', mock.Mock())
    @mock.patch('requests.get', mock.Mock())
    def test_retry(self):
        """Tests retry logic."""

        with self.assertRaises(restclient.MaxRequestRetriesError) as cm:
            restclient.get(
                ['http://foo.com', 'http://bar.com'],
                '/baz',
                retries=3
            )
        err = cm.exception
        self.assertEqual(len(err.attempts), 6)

        # Requests are done in order, by because other methods are being
        # callled, to make test simpler, any_order is set to True so that
        # test will pass.
        requests.get.assert_has_calls([
            mock.call('http://foo.com/baz', json=None, proxies=None,
                      headers=None, auth=mock.ANY, timeout=(.5, 10),
                      stream=None),
            mock.call('http://bar.com/baz', json=None, proxies=None,
                      headers=None, auth=mock.ANY, timeout=(.5, 10),
                      stream=None),
            mock.call('http://foo.com/baz', json=None, proxies=None,
                      headers=None, auth=mock.ANY, timeout=(1.5, 10),
                      stream=None),
            mock.call('http://bar.com/baz', json=None, proxies=None,
                      headers=None, auth=mock.ANY, timeout=(1.5, 10),
                      stream=None),
            mock.call('http://foo.com/baz', json=None, proxies=None,
                      headers=None, auth=mock.ANY, timeout=(2.5, 10),
                      stream=None),
            mock.call('http://bar.com/baz', json=None, proxies=None,
                      headers=None, auth=mock.ANY, timeout=(2.5, 10),
                      stream=None),
        ], any_order=True)
        self.assertEqual(requests.get.call_count, 6)

    @mock.patch('time.sleep', mock.Mock())
    @mock.patch('requests.get',
                side_effect=requests.exceptions.ConnectionError)
    def test_retry_on_connection_error(self, _):
        """Test retry on connection error"""

        with self.assertRaises(restclient.MaxRequestRetriesError) as cm:
            restclient.get('http://foo.com', '/')
        err = cm.exception
        self.assertEqual(len(err.attempts), 5)

    @mock.patch('time.sleep', mock.Mock())
    @mock.patch('requests.get', side_effect=requests.exceptions.Timeout)
    def test_retry_on_request_timeout(self, _):
        """Test retry on request timeout"""

        with self.assertRaises(restclient.MaxRequestRetriesError) as cm:
            restclient.get('http://foo.com', '/')
        err = cm.exception
        self.assertEqual(len(err.attempts), 5)

    @mock.patch('time.sleep', mock.Mock())
    @mock.patch('requests.get', return_value=mock.MagicMock(requests.Response))
    def test_retry_on_503(self, resp_mock):
        """Test retry for status code that should be retried (e.g. 503)"""
        resp_mock.return_value.status_code = http_client.SERVICE_UNAVAILABLE

        with self.assertRaises(restclient.MaxRequestRetriesError):
            restclient.get('http://foo.com', '/')

    @mock.patch('requests.get', return_value=mock.MagicMock(requests.Response))
    def test_default_timeout_get(self, resp_mock):
        """Tests that default timeout for get request is set correctly."""
        resp_mock.return_value.status_code = http_client.OK
        resp_mock.return_value.text = 'foo'
        restclient.get('http://foo.com', '/')
        resp_mock.assert_called_with(
            'http://foo.com/', stream=None, auth=mock.ANY,
            headers=None, json=None, timeout=(0.5, 10), proxies=None
        )

    @mock.patch('requests.delete',
                return_value=mock.MagicMock(requests.Response))
    def test_default_timeout_delete(self, resp_mock):
        """Tests that default timeout for delete request is set correctly."""
        resp_mock.return_value.status_code = http_client.OK
        resp_mock.return_value.text = 'foo'
        restclient.delete('http://foo.com', '/')
        resp_mock.assert_called_with(
            'http://foo.com/', stream=None, auth=mock.ANY,
            headers=None, json=None, timeout=(0.5, None), proxies=None
        )

    @mock.patch('requests.post',
                return_value=mock.MagicMock(requests.Response))
    def test_default_timeout_post(self, resp_mock):
        """Tests that default timeout for post request is set correctly."""
        resp_mock.return_value.status_code = http_client.OK
        resp_mock.return_value.text = 'foo'
        restclient.post('http://foo.com', '/', '')
        resp_mock.assert_called_with(
            'http://foo.com/', stream=None, auth=mock.ANY,
            headers=None, json='', timeout=(0.5, None), proxies=None
        )

    @mock.patch('requests.put', return_value=mock.MagicMock(requests.Response))
    def test_default_timeout_put(self, resp_mock):
        """Tests that default timeout for put request is set correctly."""
        resp_mock.return_value.status_code = http_client.OK
        resp_mock.return_value.text = 'foo'
        restclient.put('http://foo.com', '/', '')
        resp_mock.assert_called_with(
            'http://foo.com/', stream=None, auth=mock.ANY,
            headers=None, json='', timeout=(0.5, None), proxies=None
        )


if __name__ == '__main__':
    unittest.main()
