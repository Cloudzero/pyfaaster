# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import re
from boto3.dynamodb.types import TypeSerializer, TypeDeserializer

pattern = re.compile(r'[\W_]+', re.UNICODE)


def update_item_from_dict(table_name, key, dictionary, client):
    """
    Update the item identified by `key` in the DynamoDB `table` by adding
    all of the attributes in the `dictionary`.
    Args:
        table_name (str):
        key (dict):
        dictionary (dict):
        client:

    Returns:
        dict
    """
    serializer = TypeSerializer()
    deserializer = TypeDeserializer()

    # Convert all keys to alphanumeric
    dictionary = {pattern.sub("", k): v for k, v in dictionary.items()}

    updates_string = ', '.join([f'#{k} = :{k}' for k in dictionary.keys()])
    update_expression = f'SET {updates_string}'
    attribute_names = {f'#{k}': k for k in dictionary.keys()}
    attribute_values = {f':{k}': serializer.serialize(v) for k, v in dictionary.items()}
    item = client.update_item(
        TableName=table_name,
        Key={k: serializer.serialize(v) for k, v in key.items()},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=attribute_names,
        ExpressionAttributeValues=attribute_values,
        ReturnValues='ALL_NEW',
    )
    if item:
        result_data = item.get('Attributes', {})
        output_data = {}
        for k, v in result_data.items():
            output_data[k] = deserializer.deserialize(v)
        return output_data
    else:
        return None
