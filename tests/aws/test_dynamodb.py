# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import botocore.session
import pytest
from botocore.stub import Stubber

import pyfaaster.aws.dynamodb as dyn


@pytest.mark.unit
def test_update_item_from_dict():
    client = botocore.session.get_session().create_client('dynamodb')

    expected_update_item_response = {
        'Attributes': {'id': {'S': '1'}, 'name': {'S': 'Harry'}, 'best-friend': {'S': 'Lloyd'}},
        'ConsumedCapacity': {},
        'ItemCollectionMetrics': {}}
    expected_update_item_parameters = {'ExpressionAttributeNames': {'#bestfriend': 'best-friend'},
                                       'ExpressionAttributeValues': {':bestfriend': {'S': 'Lloyd'}},
                                       'Key': {'id': {'S': '1'}},
                                       'ReturnValues': 'ALL_NEW',
                                       'TableName': 'test_table',
                                       'UpdateExpression': 'SET #bestfriend = :bestfriend'}
    with Stubber(client) as stubber:
        stubber.add_response('update_item', expected_update_item_response, expected_update_item_parameters)
        attributes = {'best-friend': 'Lloyd'}
        item = dyn.update_item_from_dict('test_table', {'id': '1'}, attributes, client)
        assert item == {'id': '1', 'name': 'Harry', 'best-friend': 'Lloyd'}


@pytest.mark.unit
def test_update_item_from_dict_reserved_words():
    client = botocore.session.get_session().create_client('dynamodb')

    expected_update_item_response = {
        'Attributes': {'id': {'S': '1'}, 'name': {'S': 'Harry'}, 'AGGREGATE': {'S': 'Lloyd'}},
        'ConsumedCapacity': {},
        'ItemCollectionMetrics': {}}
    expected_update_item_parameters = {'ExpressionAttributeNames': {'#AGGREGATE': 'AGGREGATE'},
                                       'ExpressionAttributeValues': {':AGGREGATE': {'S': 'Lloyd'}},
                                       'Key': {'id': {'S': '1'}},
                                       'ReturnValues': 'ALL_NEW',
                                       'TableName': 'test_table',
                                       'UpdateExpression': 'SET #AGGREGATE = :AGGREGATE'}
    with Stubber(client) as stubber:
        stubber.add_response('update_item', expected_update_item_response, expected_update_item_parameters)
        attributes = {'AGGREGATE': 'Lloyd'}
        item = dyn.update_item_from_dict('test_table', {'id': '1'}, attributes, client)
        assert item == {'id': '1', 'name': 'Harry', 'AGGREGATE': 'Lloyd'}
