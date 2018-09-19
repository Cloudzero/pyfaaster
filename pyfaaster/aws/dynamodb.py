# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


def update_item_from_dict(table, key, dictionary):
    """Update the item identified by `key` in the DynamoDB `table` by adding
    all of the attributes in the `dictionary`.
    """
    updates_list = [f'{k} = :{k}' for k in dictionary.keys()]
    updates_string = ', '.join(updates_list)
    update_expression = f'SET {updates_string}'
    attribute_values = {f':{k}': v for k, v in dictionary.items()}
    item = table.update_item(
        Key=key,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=attribute_values,
    )
    return item['Attributes'] if item else None
