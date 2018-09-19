# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import boto3
import moto
import pytest

import pyfaaster.aws.dynamodb as dyn


def create_test_table(client, name):
    client.create_table(TableName=name,
                        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
                        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
                        ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1})


@pytest.mark.unit
@moto.mock_dynamodb2
@moto.mock_sts
def test_update_item_from_dict():
    client = boto3.client('dynamodb')
    create_test_table(client, 'test-table')
    table = boto3.resource('dynamodb').Table('test-table')
    table.put_item(Item={'id': '1', 'name': 'Harry'})

    attributes = {'best-friend': 'Lloyd'}
    item = dyn.update_item_from_dict(table, {'id': '1'}, attributes)
    assert item == {'id': '1', 'name': 'Harry', 'best-friend': 'Lloyd'}


@pytest.mark.unit
@moto.mock_dynamodb2
@moto.mock_sts
def test_update_item_from_dict_reserved_words():
    client = boto3.client('dynamodb')
    create_test_table(client, 'test-table')
    table = boto3.resource('dynamodb').Table('test-table')
    table.put_item(Item={'id': '1', 'name': 'Harry'})

    attributes = {'AGGREGATE': 'Lloyd'}
    item = dyn.update_item_from_dict(table, {'id': '1'}, attributes)
    assert item == {'id': '1', 'name': 'Harry', 'AGGREGATE': 'Lloyd'}
