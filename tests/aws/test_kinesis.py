# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import pytest

import pyfaaster.aws.kinesis as kinesis


@pytest.mark.unit
def test_decode_record_uncompressed():
    s64 = b'cGhlbm9tZW5hbCBjb3NtaWMgcG93ZXJz'
    record = {'kinesis': {'data': s64}}
    assert kinesis.decode_record(record) == 'phenomenal cosmic powers'


@pytest.mark.unit
def test_decode_record_compressed():
    s64 = b'H4sIAIoX6loC/8ssKalUSMoEkTmZZZl56QrFBYnJqQC7waqcFwAAAA=='
    record = {'kinesis': {'data': s64}}
    assert kinesis.decode_record(record, compressed=True) == 'itty bitty living space'


@pytest.mark.unit
def test_decode_records_with_transform():
    s64 = b'cGhlbm9tZW5hbCBjb3NtaWMgcG93ZXJz'
    records = [{'kinesis': {'data': s64}}]
    [actual] = kinesis.decode_records(records, transform_fn=lambda s: s.upper())
    assert actual == 'PHENOMENAL COSMIC POWERS'
