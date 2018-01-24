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

    conn['s3_client'].create_bucket(Bucket=bucket_name)

    settings = {
        'setting_1': {
            'value': 'foo',
            'encrypted': False,
        },
    }
    saved_settings = conf.save(conn, bucket_name, file_name, settings)

    loaded_settings = conf.load(conn, bucket_name, file_name)
    assert saved_settings == settings
    assert loaded_settings == settings


@pytest.mark.unit
@moto.mock_s3
@moto.mock_kms
@moto.mock_sts
def test_configuration_encrypted():
    encrypt_key_arn = 'arn:aws:kms:region:account_id:key/guid'
    bucket_name = 'bucket'
    file_name = 'conf.json'
    conn = conf.conn(encrypt_key_arn)

    conn['s3_client'].create_bucket(Bucket=bucket_name)

    settings = {
        'setting_1': {
            'value': 'foo',
            'encrypted': True,
        },
    }
    saved_settings = conf.save(conn, bucket_name, file_name, settings)

    loaded_settings = conf.load(conn, bucket_name, file_name)
    assert saved_settings != settings
    assert loaded_settings == settings
