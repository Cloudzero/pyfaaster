# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import os
import pytest
import simplejson as json

import pyfaaster.aws.handlers_decorators_v2 as decs
from czc.unittest import Context
import datetime as dt
import botocore.session
import freezegun
from voluptuous import Invalid

from tests.aws.common import MockContext
from botocore.stub import Stubber
import pyfaaster.aws.publish as pub

_CONFIG_BUCKET = 'example_config_bucket'


@pytest.fixture(scope='function')
def context(mocker):
    region = 'us-east-1'
    account_id = '123456789012'
    namespace = 'test-ns'
    sns = botocore.session.get_session().create_client('sns')
    conn = pub.conn(region, account_id, namespace, client=sns)

    with Context(mocker, decs, modules_to_mock=['publish.conn']) as context:
        orig_env = os.environ.copy()
        os.environ['NAMESPACE'] = 'test-ns'
        os.environ['CONFIG'] = _CONFIG_BUCKET
        os.environ['ENCRYPT_KEY_ARN'] = 'arn'
        context.os = {'environ': os.environ}
        context.region = region
        context.account_id = account_id
        context.lambda_context = MockContext(f'arn:aws:lambda:{context.region}:{context.account_id}')
        context.sns = sns
        context.mock_publish_conn.return_value = conn
        yield context

    mocker.stopall()
    os.environ = orig_env


@pytest.mark.unit
def test_publisher(context, mocker):
    namespace = os.environ['NAMESPACE']
    messages = {
        f'system-{namespace}-topic-1': 'String Message',
        f'system-{namespace}-topic-2': {'message': 'string', 'timestamp': 'this feature is stupid'}
    }

    response = {
        'ResponseMetadata': {
            'RequestId': 1234,
            'HTTPStatusCode': 200,
        }
    }

    event = {
        'message': {
            'foo': 'bar'
        }
    }

    @decs.publisher
    def test(event, context, **kwargs):
        return {
            'messages': messages
        }

    with Stubber(context.sns) as stubber:
        for topic, message in messages.items():
            if isinstance(message, str):
                stubber.add_response('publish', response, {'TopicArn': f'arn:aws:sns:{context.region}:{context.account_id}:{topic}', 'Message': message})
            else:
                stubber.add_response('publish', response,
                                     {'TopicArn': f'arn:aws:sns:{context.region}:{context.account_id}:{topic}',
                                      'Message': json.dumps(message, iterable_as_array=True)})

        test(event, context.lambda_context)


@pytest.mark.unit
def test_event_publisher_no_events(context):
    incoming_event = {
        'message': {
            'foo': 'bar'
        }
    }

    @decs.event_publisher
    def test(event, context, **kwargs):
        return {
        }

    with Stubber(context.sns):
        test(incoming_event, context.lambda_context)


@freezegun.freeze_time('2020-01-01')
@pytest.mark.unit
def test_event_publisher_sns_events(context):
    namespace = os.environ['NAMESPACE']
    incoming_event = {
        'message': {
            'foo': 'bar'
        }
    }

    response = {
        'ResponseMetadata': {
            'RequestId': 1234,
            'HTTPStatusCode': 200,
        },
    }

    events = {
        f'system-{namespace}-topic-1': [
            {'type': 'first-event', 'detail': {'message': 'this feature is stupid'}},
            {'type': 'second-event', 'detail': {'timestamp': 'this event is stupid'}},
        ],
        f'system-{namespace}-topic-2': [
            {'type': 'third-event', 'detail': {'timestamp': 'this feature is stupid'}}
        ]
    }

    @decs.event_publisher
    def test(event, context, **kwargs):
        return {
            'events': events
        }

    with Stubber(context.sns) as stubber:
        for topic, events_for_topic in events.items():
            for event in events_for_topic:
                expected_event = {
                    **event['detail']
                }

                if 'timestamp' not in expected_event:
                    expected_event['timestamp'] = str(dt.datetime.now(tz=dt.timezone.utc))
                stubber.add_response('publish', response, {
                    'TopicArn': f'arn:aws:sns:{context.region}:{context.account_id}:{topic}',
                    'Message': json.dumps(expected_event, iterable_as_array=True),
                    'Subject': event['type'],
                    'MessageAttributes': {
                        'message_type': {
                            'DataType': 'String',
                            'StringValue': event['type']
                        }
                    }
                })

        test(incoming_event, context.lambda_context)


@pytest.mark.parametrize('events', [
    {
        'system-test-topic-1': [{}]  # No event data
    },
    {
        'system-test-topic-1': [{'eventName': 'valid-event', 'detail': {'timestamp': 'this feature is stupid'}}, {}]  # One good, one bad
    },
    {
        'system-test-topic-1': [{'eventName': 'valid-event'}]  # No detail
    },
    {
        'system-test-topic-1': [{'detail': {'timestamp': 'this feature is stupid'}}]  # No eventName
    },
    {
        'system-test-topic-1': [{'eventName': {'timestamp': 'this feature is stupid'}, 'detail': {}}]  # Invalid type for eventName
    },
    {
        'system-test-topic-1': [{'eventName': 'test', 'detail': 'this is not the right type'}]  # Invalid type for detail
    }
])
@pytest.mark.unit
def test_event_publisher_catches_bad_events(context, events):
    incoming_event = {
        'message': {
            'foo': 'bar'
        }
    }

    @decs.event_publisher
    def test(event, context, **kwargs):
        return {
            'events': events
        }

    with Stubber(context.sns):
        with pytest.raises(Invalid):
            test(incoming_event, context.lambda_context)
