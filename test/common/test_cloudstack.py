import httplib
import sys
import unittest
import urlparse

try:
    import simplejson as json
except ImportError:
    import json

try:
    parse_qsl = urlparse.parse_qsl
except AttributeError:
    import cgi
    parse_qsl = cgi.parse_qsl

from libcloud.common.cloudstack import CloudStackConnection, CloudStackResponse
from libcloud.common.types import MalformedResponseError

from test import MockHttpTestCase

async_delay = 0

class CloudStackMockDriver(object):
    host = 'nonexistant.'
    path = '/path'
    async_poll_frequency = 0

    name = 'fake'

    async_delay = 0

class CloudStackCommonTest(unittest.TestCase):
    def setUp(self):
        CloudStackConnection.conn_classes = (None, CloudStackMockHttp)
        self.connection = CloudStackConnection('apikey', 'secret',
                                               host=CloudStackMockDriver.host)
        self.connection.poll_interval = 0.0
        self.driver = self.connection.driver = CloudStackMockDriver()

    def test_sync_request_bad_response(self):
        self.driver.path = '/bad/response'
        try:
            self.connection._sync_request('fake')
        except Exception, e:
            self.assertTrue(isinstance(e, MalformedResponseError))
            return
        self.assertTrue(False)

    def test_sync_request(self):
        self.driver.path = '/sync'
        self.connection._sync_request('fake')

    def test_async_request_successful(self):
        self.driver.path = '/async/success'
        result = self.connection._async_request('fake')
        self.assertEqual(result, {'fake': 'result'})

    def test_async_request_unsuccessful(self):
        self.driver.path = '/async/fail'
        try:
            self.connection._async_request('fake')
        except:
            return
        self.assertFalse(True)

    def test_async_request_delayed(self):
        global async_delay
        self.driver.path = '/async/delayed'
        async_delay = 2
        self.connection._async_request('fake')
        self.assertEqual(async_delay, 0)

    def test_signature_algorithm(self):
        cases = [
            (
                {
                    'command': 'listVirtualMachines'
                }, 'z/a9Y7J52u48VpqIgiwaGUMCso0='
            ), (
                {
                    'command': 'deployVirtualMachine',
                    'name': 'fred',
                    'displayname': 'George',
                    'serviceofferingid': 5,
                    'templateid': 17,
                    'zoneid': 23,
                    'networkids': 42
                 }, 'gHTo7mYmadZ+zluKHzlEKb1i/QU='
            ), (
                {
                    'command': 'deployVirtualMachine',
                    'name': 'fred',
                    'displayname': 'George+Ringo',
                    'serviceofferingid': 5,
                    'templateid': 17,
                    'zoneid': 23,
                    'networkids': 42
                 }, 'tAgfrreI1ZvWlWLClD3gu4+aKv4='
            )
        ]

        connection = CloudStackConnection('fnord', 'abracadabra')
        for case in cases:
            params = connection.add_default_params(case[0])
            self.assertEqual(connection._make_signature(params), case[1])

class CloudStackMockHttp(MockHttpTestCase):
    def _response(self, status, result, response):
        return (status, json.dumps(result), result, response)

    def _check_request(self, url):
        url = urlparse.urlparse(url)
        query = dict(parse_qsl(url.query))

        self.assertTrue('apiKey' in query)
        self.assertTrue('command' in query)
        self.assertTrue('response' in query)
        self.assertTrue('signature' in query)

        self.assertTrue(query['response'] == 'json')

        return query

    def _bad_response(self, method, url, body, headers):
        self._check_request(url)
        result = {'success': True}
        return self._response(httplib.OK, result, httplib.responses[httplib.OK])

    def _sync(self, method, url, body, headers):
        query = self._check_request(url)
        result = {query['command'].lower() + 'response': {}}
        return self._response(httplib.OK, result, httplib.responses[httplib.OK])

    def _async_success(self, method, url, body, headers):
        query = self._check_request(url)
        if query['command'].lower() == 'queryasyncjobresult':
            self.assertEqual(query['jobid'], '42')
            result = {
                query['command'].lower() + 'response': {
                    'jobstatus': 1,
                    'jobresult': {'fake': 'result'}
                }
            }
        else:
            result = {query['command'].lower() + 'response': {'jobid': '42'}}
        return self._response(httplib.OK, result, httplib.responses[httplib.OK])

    def _async_fail(self, method, url, body, headers):
        query = self._check_request(url)
        if query['command'].lower() == 'queryasyncjobresult':
            self.assertEqual(query['jobid'], '42')
            result = {
                query['command'].lower() + 'response': {
                    'jobstatus': 2,
                    'jobresult': {'fake': 'failresult'}
                }
            }
        else:
            result = {query['command'].lower() + 'response': {'jobid': '42'}}
        return self._response(httplib.OK, result, httplib.responses[httplib.OK])

    def _async_delayed(self, method, url, body, headers):
        global async_delay

        query = self._check_request(url)
        if query['command'].lower() == 'queryasyncjobresult':
            self.assertEqual(query['jobid'], '42')
            if async_delay == 0:
                result = {
                    query['command'].lower() + 'response': {
                        'jobstatus': 1,
                        'jobresult': {'fake': 'result'}
                    }
                }
            else:
                result = {
                    query['command'].lower() + 'response': {
                        'jobstatus': 0,
                    }
                }
                async_delay -= 1
        else:
            result = {query['command'].lower() + 'response': {'jobid': '42'}}
        return self._response(httplib.OK, result, httplib.responses[httplib.OK])

if __name__ == '__main__':
    sys.exit(unittest.main())
