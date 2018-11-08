# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import pytest
import botocore.session
import simplejson as json

from botocore.stub import Stubber

import pyfaaster.aws.publish as pub


@pytest.mark.unit
def test_publish():
    region = 'us-east-1'
    account_id = '123456789012'
    namespace = 'test'

    sns = botocore.session.get_session().create_client('sns')

    response = {
        'ResponseMetadata': {
            'RequestId': 1234,
            'HTTPStatusCode': 200,
        }
    }

    conn = pub.conn(region, account_id, namespace, client=sns)
    with Stubber(sns) as stubber:

        messages = {
            f'arn:aws:sns:{region}:{account_id}:system-{namespace}-topic-1': 'String Message',
            f'arn:aws:sns:{region}:{account_id}:system-{namespace}-topic-2': {'message': 'string',
                                                                              'timestamp': 'this feature is stupid'}
        }
        for topic, message in messages.items():
            if isinstance(message, str):
                stubber.add_response('publish', response, {'TopicArn': topic, 'Message': message})
            else:
                stubber.add_response('publish', response,
                                     {'TopicArn': topic,
                                      'Message': json.dumps(message, iterable_as_array=True)})

        published_messages = pub.publish(conn, messages)

    assert len(published_messages) == 2
