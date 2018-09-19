# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


def update_item_from_dict(table, key, dictionary):
    """Update the item identified by `key` in the DynamoDB `table` by adding
    all of the attributes in the `dictionary`.
    """
    updates_string = ', '.join([f'#{k} = :{k}' for k in dictionary.keys()])
    update_expression = f'SET {updates_string}'
    attribute_names = {f'#{k}': k for k in dictionary.keys()}
    attribute_values = {f':{k}': v for k, v in dictionary.items()}
    item = table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeNames=attribute_names,
        ExpressionAttributeValues=attribute_values,
        ReturnValues='ALL_NEW',
    )
    return item.get('Attributes', {}) if item else None
