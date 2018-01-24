# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import moto
import pytest

import pyfaaster.aws.publish as pub


@pytest.mark.unit
@moto.mock_sns
@moto.mock_sts
def test_publish():
    region = 'us-east-1'
    account_id = '123456789012'
    namespace = 'test'
    conn = pub.conn(region, account_id, namespace)

    messages = {
        'system-{namespace}-topic-1': 'String Message',
        'system-{namespace}-topic-2': {'message': 'string'},
    }
    for topic, _ in messages.items():
        topic_name = topic.format(namespace=namespace)
        arn = conn['sns'].create_topic(Name=topic_name)
        print(f'{topic}: {arn}')

    res = pub.publish(conn, messages)
    assert res
