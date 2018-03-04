# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import boto3
import simplejson as json
import datetime as dt

import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


def publish(conn, messages):
    logger.debug(f'Publishing {messages}')

    published_messages = []
    for topic, message in messages.items():
        topic_arn = topic.format(
            namespace=conn['namespace']) if 'arn:aws:sns' in topic else conn['topic_arn_prefix'] + topic.format(namespace=conn['namespace'])
        message = messages[topic]
        if getattr(message, 'get', None) and not message.get('timestamp'):
            message['timestamp'] = str(dt.datetime.now(tz=dt.timezone.utc))
        logger.debug(f'Publishing {message} to {topic_arn}')
        conn['sns'].publish(
            TopicArn=topic_arn,
            Message=json.dumps(message),
        )
        published_messages.append(message)
    return published_messages


def conn(region, account_id, namespace):
    return {
        'namespace': namespace,
        'topic_arn_prefix': f'arn:aws:sns:{region}:{account_id}:',
        'sns': boto3.client('sns'),
    }
