# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.
from io import BytesIO

import botocore.session
from botocore.stub import Stubber
from botocore.response import StreamingBody
import simplejson as json
import pytest

import pyfaaster.aws.configuration as conf


@pytest.mark.unit
def test_configuration():
    encrypt_key_arn = 'arn:aws:kms:region:account_id:key/guid'
    bucket_name = 'bucket'
    file_name = 'conf.json'
    settings = {
        'setting_1': 'foo'
    }
    s3 = botocore.session.get_session().create_client('s3')
    conn = conf.conn(encrypt_key_arn, client=s3)

    expected_put_response = {
        'Expiration': 'string',
        'ETag': 'string',
        'ServerSideEncryption': 'AES256',
        'VersionId': 'string',
        'SSECustomerAlgorithm': 'string',
        'SSECustomerKeyMD5': 'string',
        'SSEKMSKeyId': 'string',
        'RequestCharged': 'requester'
    }

    put_parameters = {'Body': json.dumps(settings),
                      'Bucket': bucket_name,
                      'Key': file_name,
                      'SSEKMSKeyId': 'arn:aws:kms:region:account_id:key/guid',
                      'ServerSideEncryption': 'aws:kms'}
    data = BytesIO(json.dumps(settings).encode('utf-8'))
    # data.seek(0)
    expected_get_response = {'Body': StreamingBody(raw_stream=data, content_length=20)}
    get_parameters = {'Bucket': bucket_name, 'Key': file_name}

    with Stubber(s3) as stubber:
        stubber.add_response('put_object', expected_put_response, put_parameters)
        saved_settings = conf.save(conn, bucket_name, file_name, settings)

        stubber.add_response('get_object', expected_get_response, get_parameters)
        loaded_settings = conf.load(conn, bucket_name, file_name)
    assert saved_settings == settings
    assert loaded_settings == settings


@pytest.mark.unit
def test_configuration_no_encrypt_key():
    bucket_name = 'bucket'
    file_name = 'conf.json'
    settings = {
        'setting_1': 'foo'
    }
    s3 = botocore.session.get_session().create_client('s3')
    conn = conf.conn(client=s3)

    expected_put_response = {
        'Expiration': 'string',
        'ETag': 'string',
        'ServerSideEncryption': 'AES256',
        'VersionId': 'string',
        'SSECustomerAlgorithm': 'string',
        'SSECustomerKeyMD5': 'string',
        'SSEKMSKeyId': 'string',
        'RequestCharged': 'requester'
    }

    put_parameters = {'Body': json.dumps(settings),
                      'Bucket': bucket_name,
                      'Key': file_name,
                      'ServerSideEncryption': 'AES256'}
    data = BytesIO(json.dumps(settings).encode('utf-8'))
    # data.seek(0)
    expected_get_response = {'Body': StreamingBody(raw_stream=data, content_length=20)}
    get_parameters = {'Bucket': bucket_name, 'Key': file_name}

    with Stubber(s3) as stubber:
        stubber.add_response('put_object', expected_put_response, put_parameters)
        saved_settings = conf.save(conn, bucket_name, file_name, settings)

        stubber.add_response('get_object', expected_get_response, get_parameters)
        loaded_settings = conf.load(conn, bucket_name, file_name)
    assert saved_settings == settings
    assert loaded_settings == settings


@pytest.mark.unit
def test_read_only():
    encrypt_key_arn = 'arn:aws:kms:region:account_id:key/guid'
    bucket_name = 'bucket'
    file_name = 'conf.json'
    settings = {
        'setting_1': 'foo'
    }
    s3 = botocore.session.get_session().create_client('s3')
    conn = conf.conn(encrypt_key_arn, client=s3)

    expected_put_response = {
        'Expiration': 'string',
        'ETag': 'string',
        'ServerSideEncryption': 'AES256',
        'VersionId': 'string',
        'SSECustomerAlgorithm': 'string',
        'SSECustomerKeyMD5': 'string',
        'SSEKMSKeyId': 'string',
        'RequestCharged': 'requester'
    }

    put_parameters = {'Body': json.dumps(settings),
                      'Bucket': bucket_name,
                      'Key': file_name,
                      'SSEKMSKeyId': 'arn:aws:kms:region:account_id:key/guid',
                      'ServerSideEncryption': 'aws:kms'}
    data = BytesIO(json.dumps(settings).encode('utf-8'))
    # data.seek(0)
    expected_get_response = {'Body': StreamingBody(raw_stream=data, content_length=20)}
    get_parameters = {'Bucket': bucket_name, 'Key': file_name}

    with Stubber(s3) as stubber:
        # verify we can put data in
        stubber.add_response('put_object', expected_put_response, put_parameters)
        saved_settings = conf.save(conn, bucket_name, file_name, settings)
        assert saved_settings == settings

        # verify we can get data out
        stubber.add_response('get_object', expected_get_response, get_parameters)
        loaded_settings = conf.read_only(conn, bucket_name, file_name)
        assert loaded_settings == settings

        # verify cache has data
        assert conf.read_only_cache.currsize == 1
        # verify cache has the right data
        assert conf.read_only_cache[('bucket', 'conf.json')] == settings
