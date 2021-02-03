# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import boto3
import simplejson as json
import datetime as dt

import pyfaaster.aws.tools as tools
from voluptuous import Schema, ALLOW_EXTRA, All

logger = tools.setup_logging('pyfaaster')


def _publish_sns_message(conn, topic, message, **kwargs):
    logger.debug(f'Publishing {message}')

    topic_arn = topic.format(
        namespace=conn['namespace']) if 'arn:aws:sns' in topic else conn['topic_arn_prefix'] + topic.format(
        namespace=conn['namespace'])

    if getattr(message, 'get', None) and not message.get('timestamp'):
        message['timestamp'] = str(dt.datetime.now(tz=dt.timezone.utc))

    if isinstance(message, str):
        prepared_message = message
    else:
        prepared_message = json.dumps(message, iterable_as_array=True)

    logger.debug(f'Publishing {message} to {topic_arn}')

    conn['sns'].publish(
        TopicArn=topic_arn,
        Message=prepared_message,
        **kwargs
    )

    return message


EVENT = Schema({
    'type': str,
    'detail': dict
}, required=True, extra=ALLOW_EXTRA)


_validate_events = Schema({
    All(): [EVENT]
})


def publish_events(conn, events):
    _validate_events(events)
    logger.debug(f'Publishing {events}')

    published_events = []
    for topic, events_for_topic in events.items():
        for event in events_for_topic:
            event = _publish_sns_message(conn, topic, event['detail'],
                                         Subject=event['type'],
                                         MessageAttributes={
                                            'message_type': {
                                                'DataType': 'String',
                                                'StringValue': event['type']
                                            }
                                        })
            published_events.append(event)

    return published_events


def publish(conn, messages):
    logger.debug(f'Publishing {messages}')

    published_messages = []
    for topic, message in messages.items():
        message = _publish_sns_message(conn, topic, messages[topic])
        published_messages.append(message)

    return published_messages


def conn(region, account_id, namespace, client=None):
    return {
        'namespace': namespace,
        'topic_arn_prefix': f'arn:aws:sns:{region}:{account_id}:',
        'sns': client or boto3.client('sns'),
    }
