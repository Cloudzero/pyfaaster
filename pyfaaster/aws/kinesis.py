# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import base64
import gzip


def decode_record(record, compressed=False, fn=lambda x: x):
    data = record['kinesis']['data']
    decoded = base64.b64decode(data)
    return fn((decoded if not compressed else gzip.decompress(decoded)).decode('utf-8'))


def decode_records(records, compressed=False, fn=lambda x: x):
    return [decode_record(r, compressed, fn)
            for r in records]
