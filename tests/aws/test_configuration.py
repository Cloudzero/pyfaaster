# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import moto
import pytest

import pyfaaster.aws.configuration as conf


@pytest.mark.unit
@moto.mock_s3
@moto.mock_kms
@moto.mock_sts
def test_configuration():
    encrypt_key_arn = 'arn:aws:kms:region:account_id:key/guid'
    bucket_name = 'bucket'
    file_name = 'conf.json'
    conn = conf.conn(encrypt_key_arn)

    conn['session'].client('s3').create_bucket(Bucket=bucket_name)

    settings = {
        'setting_1': 'foo',
    }
    saved_settings = conf.save(conn, bucket_name, file_name, settings)

    loaded_settings = conf.load(conn, bucket_name, file_name)
    assert saved_settings == settings
    assert loaded_settings == settings


@pytest.mark.unit
@moto.mock_s3
@moto.mock_kms
@moto.mock_sts
def test_read_only():
    encrypt_key_arn = 'arn:aws:kms:region:account_id:key/guid'
    bucket_name = 'bucket'
    file_name = 'conf.json'
    conn = conf.conn(encrypt_key_arn)

    conn['session'].client('s3').create_bucket(Bucket=bucket_name)

    settings = {
        'setting_1': 'foo',
    }
    saved_settings = conf.save(conn, bucket_name, file_name, settings)

    loaded_settings = conf.read_only(bucket_name, file_name)

    N = 10
    for i in range(N):
        conf.read_only(bucket_name, file_name)

    assert conf.read_only.cache_info().misses == 1
    assert conf.read_only.cache_info().hits == N
    assert saved_settings == settings
    assert loaded_settings == settings
