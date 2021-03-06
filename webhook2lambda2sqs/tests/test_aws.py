"""
The latest version of this package is available at:
<http://github.com/jantman/webhook2lambda2sqs>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of webhook2lambda2sqs, also known as webhook2lambda2sqs.

    webhook2lambda2sqs is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    webhook2lambda2sqs is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with webhook2lambda2sqs.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/webhook2lambda2sqs> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import sys
import pytest
from pprint import pformat
from time import tzset
import os

from webhook2lambda2sqs.aws import AWSInfo
from webhook2lambda2sqs.tests.support import exc_msg

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, call, Mock, DEFAULT, PropertyMock  # noqa
else:
    from unittest.mock import patch, call, Mock, DEFAULT, PropertyMock  # noqa

pbm = 'webhook2lambda2sqs.aws'
pb = '%s.AWSInfo' % pbm


class TestAWSInfo(object):

    def setup(self):
        self.conf = {}

        def se_get(k):
            return self.conf.get(k, None)

        config = Mock()
        config.get.side_effect = se_get
        type(config).func_name = 'myfname'
        self.cls = AWSInfo(config)

    def test_init(self):
        c = Mock()
        cls = AWSInfo(c)
        assert cls.config == c

    def test_show_cloudwatch_logs(self, capsys):
        resp = {
            'logStreams': [
                {'logStreamName': 's1'},
                {'logStreamName': 's2'},
                {'logStreamName': 's3'}
            ]
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s.client' % pbm, autospec=True) as mock_conn:
                with patch('%s._show_log_stream' % pb, autospec=True) as sls:
                    mock_conn.return_value.describe_log_streams.return_value = \
                        resp
                    sls.side_effect = [1, 10]
                    self.cls.show_cloudwatch_logs(5)
        out, err = capsys.readouterr()
        assert err == ''
        assert out == ''
        assert mock_conn.mock_calls == [
            call('logs'),
            call().describe_log_streams(descending=True, limit=5,
                                        logGroupName='/aws/lambda/myfname',
                                        orderBy='LastEventTime')
        ]
        assert sls.mock_calls == [
            call(self.cls,
                 mock_conn.return_value, '/aws/lambda/myfname', 's1', 5),
            call(self.cls,
                 mock_conn.return_value, '/aws/lambda/myfname', 's2', 4),
        ]
        assert mock_logger.mock_calls == [
            call.debug('Log Group Name: %s', '/aws/lambda/myfname'),
            call.debug('Connecting to AWS Logs API'),
            call.debug('Getting log streams'),
            call.debug('Found %d log streams', 3)
        ]

    def test_show_cloudwatch_logs_none(self, capsys):
        resp = {
            'logStreams': []
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s.client' % pbm, autospec=True) as mock_conn:
                with patch('%s._show_log_stream' % pb, autospec=True) as sls:
                    mock_conn.return_value.describe_log_streams.return_value = \
                        resp
                    sls.side_effect = [1, 10]
                    self.cls.show_cloudwatch_logs(5)
        out, err = capsys.readouterr()
        assert err == ''
        assert out == ''
        assert mock_conn.mock_calls == [
            call('logs'),
            call().describe_log_streams(descending=True, limit=5,
                                        logGroupName='/aws/lambda/myfname',
                                        orderBy='LastEventTime')
        ]
        assert sls.mock_calls == []
        assert mock_logger.mock_calls == [
            call.debug('Log Group Name: %s', '/aws/lambda/myfname'),
            call.debug('Connecting to AWS Logs API'),
            call.debug('Getting log streams'),
            call.debug('Found %d log streams', 0)
        ]

    def test_show_log_stream_none(self, capsys):
        conn = Mock()
        conn.get_log_events.return_value = {'events': []}
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            res = self.cls._show_log_stream(conn, 'gname', 'sname')
        assert res == 0
        out, err = capsys.readouterr()
        assert err == ''
        assert out == ''
        assert conn.mock_calls == [
            call.get_log_events(logGroupName='gname', logStreamName='sname',
                                limit=10, startFromHead=False)
        ]
        assert mock_logger.mock_calls == [
            call.debug('Showing up to %d events from stream %s', 10, 'sname'),
            call.debug('displayed %d events from stream', 0)
        ]

    def test_show_log_stream(self, capsys):
        # make sure we have the timezone we expect
        os.environ['TZ'] = 'UTC'
        tzset()
        conn = Mock()
        conn.get_log_events.return_value = {
            'events': [
                {
                    'timestamp': 1468785496000,  # 2016-07-17 19:58:16
                    'message': 'msg1'
                },
                {
                    'timestamp': 1468782120000,  # 2016-07-17 19:02:00
                    'message': 'msg2'
                },
                {
                    'timestamp': 1468781640000,  # 2016-07-17 18:54:00
                    'message': 'msg3'
                },
                {
                    'timestamp': 1468779683000,  # 2016-07-17 18:21:23
                    'message': 'msg4'
                },
            ]
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            res = self.cls._show_log_stream(conn, 'gname', 'sname', max_count=2)
        assert res == 2
        out, err = capsys.readouterr()
        assert err == ''
        assert out == "## Log Group 'gname'; Log Stream 'sname'\n" \
                      "2016-07-17 19:58:16 => msg1\n" \
                      "2016-07-17 19:02:00 => msg2\n"
        assert conn.mock_calls == [
            call.get_log_events(logGroupName='gname', logStreamName='sname',
                                limit=2, startFromHead=False)
        ]
        assert mock_logger.mock_calls == [
            call.debug('Showing up to %d events from stream %s', 2, 'sname'),
            call.debug('displayed %d events from stream', 2)
        ]

    def test_all_queue_names(self):
        self.conf = {
            'endpoints': {
                'foo': {
                    'queues': ['foo1', 'foo2']
                },
                'bar': {
                    'queues': ['bar1']
                },
                'baz': {
                    'queues': ['baz1', 'foo1']
                }
            }
        }
        assert self.cls._all_queue_names == ['bar1', 'baz1', 'foo1', 'foo2']

    def test_show_queue_by_name(self):
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s.client' % pbm, autospec=True) as mock_sqs:
                with patch('%s._show_one_queue' % pb,
                           autospec=True) as mock_show:
                    with patch('%s._all_queue_names' % pb,
                               new_callable=PropertyMock, create=True
                               ) as mock_aqn:
                        mock_aqn.return_value = []
                        self.cls.show_queue(name='foo')
        assert mock_sqs.mock_calls == [call('sqs')]
        assert mock_show.mock_calls == [
            call(self.cls, mock_sqs.return_value, 'foo', 10, delete=False)
        ]
        assert mock_logger.mock_calls == [
            call.debug('Connecting to SQS API')
        ]
        assert mock_aqn.mock_calls == []

    def test_show_queue_all(self):
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s.client' % pbm, autospec=True) as mock_sqs:
                with patch('%s._show_one_queue' % pb,
                           autospec=True) as mock_show:
                    with patch('%s._all_queue_names' % pb,
                               new_callable=PropertyMock, create=True
                               ) as mock_aqn:
                        mock_aqn.return_value = ['foo', 'bar', 'baz']
                        self.cls.show_queue(count=3, delete=True)
        assert mock_sqs.mock_calls == [call('sqs')]
        assert mock_show.mock_calls == [
            call(self.cls, mock_sqs.return_value, 'foo', 3, delete=True),
            call(self.cls, mock_sqs.return_value, 'bar', 3, delete=True),
            call(self.cls, mock_sqs.return_value, 'baz', 3, delete=True)
        ]
        assert mock_logger.mock_calls == [
            call.debug('Connecting to SQS API')
        ]
        assert mock_aqn.mock_calls == [
            call()
        ]

    def test_show_queue_too_many(self):
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s.client' % pbm, autospec=True) as mock_sqs:
                with patch('%s._show_one_queue' % pb,
                           autospec=True) as mock_show:
                    with patch('%s._all_queue_names' % pb,
                               new_callable=PropertyMock, create=True
                               ) as mock_aqn:
                        mock_aqn.return_value = ['foo', 'bar', 'baz']
                        with pytest.raises(Exception) as excinfo:
                            self.cls.show_queue(count=12, delete=True)
        assert exc_msg(excinfo.value) == 'Error: currently this script only ' \
                                         'supports receiving 10 or fewer ' \
                                         'messages per queue.'
        assert mock_sqs.mock_calls == []
        assert mock_show.mock_calls == []
        assert mock_logger.mock_calls == []
        assert mock_aqn.mock_calls == []

    def test_show_one_queue_no_delete(self, capsys):
        conn = Mock()
        conn.receive_message.return_value = {
            'Messages': [
                {'foo': 'bar', 'ReceiptHandle': 'rh1'},
                {'baz': 'blam', 'ReceiptHandle': 'rh1'},
            ]
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s._url_for_queue' % pb, autospec=True) as mock_url:
                mock_url.return_value = 'myurl'
                with patch('%s._delete_msg' % pb, autospec=True) as mock_del:
                    self.cls._show_one_queue(conn, 'foo', 3)
        out, err = capsys.readouterr()
        assert err == ''
        expected_out = "=> Queue 'foo' (myurl)\n"
        expected_out += pformat({'foo': 'bar', 'ReceiptHandle': 'rh1'}) + "\n"
        expected_out += pformat({'baz': 'blam', 'ReceiptHandle': 'rh1'}) + "\n"
        assert out == expected_out
        assert mock_del.mock_calls == []
        assert conn.mock_calls == [
            call.receive_message(
                QueueUrl='myurl',
                AttributeNames=['All'],
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=3,
                WaitTimeSeconds=20
            )
        ]
        assert mock_url.mock_calls == [
            call(self.cls, conn, 'foo')
        ]
        assert mock_logger.mock_calls == [
            call.debug("Queue '%s' url: %s", 'foo', 'myurl'),
            call.warning("Receiving %d messages from queue'%s'; this may "
                         "take up to 20 seconds.", 3, 'foo'),
            call.debug('received %d messages', 2)
        ]

    def test_show_one_queue_too_many(self, capsys):
        conn = Mock()
        conn.receive_message.return_value = {
            'Messages': [
                {'foo': 'bar', 'ReceiptHandle': 'rh1'},
                {'baz': 'blam', 'ReceiptHandle': 'rh1'},
            ]
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s._url_for_queue' % pb, autospec=True) as mock_url:
                mock_url.return_value = 'myurl'
                with patch('%s._delete_msg' % pb, autospec=True) as mock_del:
                    self.cls._show_one_queue(conn, 'foo', 1, delete=True)
        out, err = capsys.readouterr()
        assert err == ''
        expected_out = "=> Queue 'foo' (myurl)\n"
        expected_out += pformat({'foo': 'bar', 'ReceiptHandle': 'rh1'}) + "\n"
        assert out == expected_out
        assert mock_del.mock_calls == [
            call(self.cls, conn, 'myurl', 'rh1')
        ]
        assert conn.mock_calls == [
            call.receive_message(
                QueueUrl='myurl',
                AttributeNames=['All'],
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
        ]
        assert mock_url.mock_calls == [
            call(self.cls, conn, 'foo')
        ]
        assert mock_logger.mock_calls == [
            call.debug("Queue '%s' url: %s", 'foo', 'myurl'),
            call.warning("Receiving %d messages from queue'%s'; this may "
                         "take up to 20 seconds.", 1, 'foo'),
            call.debug('received %d messages', 2)
        ]

    def test_show_one_queue_empty(self, capsys):
        conn = Mock()
        conn.receive_message.return_value = {}
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s._url_for_queue' % pb, autospec=True) as mock_url:
                mock_url.return_value = 'myurl'
                with patch('%s._delete_msg' % pb, autospec=True) as mock_del:
                    self.cls._show_one_queue(conn, 'foo', 1, delete=True)
        out, err = capsys.readouterr()
        assert err == ''
        expected_out = "=> Queue 'foo' appears empty.\n"
        assert out == expected_out
        assert mock_del.mock_calls == []
        assert conn.mock_calls == [
            call.receive_message(
                QueueUrl='myurl',
                AttributeNames=['All'],
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )
        ]
        assert mock_url.mock_calls == [
            call(self.cls, conn, 'foo')
        ]
        assert mock_logger.mock_calls == [
            call.debug("Queue '%s' url: %s", 'foo', 'myurl'),
            call.warning("Receiving %d messages from queue'%s'; this may "
                         "take up to 20 seconds.", 1, 'foo'),
            call.debug('received no messages')
        ]

    def test_delete(self):
        conn = Mock()
        conn.delete_message.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            self.cls._delete_msg(conn, 'qurl', 'rh')
        assert conn.mock_calls == [
            call.delete_message(QueueUrl='qurl', ReceiptHandle='rh')
        ]
        assert mock_logger.mock_calls == [
            call.info('Message with receipt handle %s deleted from queue %s',
                      'rh', 'qurl')
        ]

    def test_delete_fail(self):
        conn = Mock()
        conn.delete_message.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 503}
        }
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            self.cls._delete_msg(conn, 'qurl', 'rh')
        assert conn.mock_calls == [
            call.delete_message(QueueUrl='qurl', ReceiptHandle='rh')
        ]
        assert mock_logger.mock_calls == [
            call.error('Error: message with receipt handle %s in queue %s '
                       'was not successfully deleted (HTTP %s)', 'rh',
                       'qurl', 503)
        ]

    def test_url_for_queue(self):
        conn = Mock()
        conn.get_queue_url.return_value = {'QueueUrl': 'myurl'}
        assert self.cls._url_for_queue(conn, 'foo') == 'myurl'
        assert conn.mock_calls == [
            call.get_queue_url(QueueName='foo')
        ]

    def test_get_api_base_url(self):
        mock_conf = Mock(region_name='myrname')
        apis = {
            'items': [
                {'name': 'foo', 'id': 'apiid1'},
                {'name': 'myfname', 'id': 'apiid2'},
                {'name': 'bar', 'id': 'apiid3'},
            ]
        }
        with patch('%s.client' % pbm, autospec=True) as mock_client:
            with patch('%s.logger' % pbm, autospec=True) as mock_logger:
                mock_client.return_value.get_rest_apis.return_value = apis
                type(mock_client.return_value)._client_config = mock_conf
                res = self.cls.get_api_base_url()
        assert res == 'https://apiid2.execute-api.myrname.amazonaws.com/' \
                      'webhook2lambda2sqs/'
        assert mock_client.mock_calls == [
            call('apigateway'),
            call().get_rest_apis()
        ]
        assert mock_logger.mock_calls == [
            call.debug('Connecting to AWS apigateway API'),
            call.debug('Found API id: %s', 'apiid2')
        ]

    def test_get_api_base_url_exception(self):
        mock_conf = Mock(region_name='myrname')
        apis = {
            'items': [
                {'name': 'foo', 'id': 'apiid1'},
                {'name': 'baz', 'id': 'apiid2'},
                {'name': 'bar', 'id': 'apiid3'},
            ]
        }
        with patch('%s.client' % pbm, autospec=True) as mock_client:
            with patch('%s.logger' % pbm, autospec=True) as mock_logger:
                mock_client.return_value.get_rest_apis.return_value = apis
                type(mock_client.return_value)._client_config = mock_conf
                with pytest.raises(Exception) as excinfo:
                    self.cls.get_api_base_url()
        assert exc_msg(excinfo.value) == 'Unable to find ReST API named myfname'
        assert mock_client.mock_calls == [
            call('apigateway'),
            call().get_rest_apis()
        ]
        assert mock_logger.mock_calls == [
            call.debug('Connecting to AWS apigateway API')
        ]
