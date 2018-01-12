# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import base64 as base
import datetime as dt
import io

import boto3
import simplejson as json

import faaster_aws.tools as tools

logger = tools.setup_logging('serveless')


def load(conn, config_bucket, config_file):
    try:
        content_object = conn['s3_client'].get_object(Bucket=config_bucket, Key=config_file)
        file_content = content_object['Body'].read().decode('utf-8')
    except Exception as error:
        logger.exception(error)
        logger.error("Could not load configuration.")
        return {}

    loaded_configuration = json.loads(file_content)
    settings = loaded_configuration.get('settings', {})
    print(f'loaded settings: {settings}')
    decrypted_settings = {k: {**v, **{'value': decrypt_text(conn, v['value'])}} if v['encrypted'] else v
                          for k, v in settings.items()}
    return decrypted_settings


def save(conn, config_bucket, config_file, settings):
    encrypted_settings = {k: {**v, **{'value': encrypt_text(conn, v['value'])}} if v['encrypted'] else v
                          for k, v in settings.items()}
    configuration = {
        'settings': encrypted_settings,
        'last_updated': dt.datetime.now(tz=dt.timezone.utc).isoformat(),
    }
    conn['s3_resource'].Object(config_bucket, config_file).put(Body=io.StringIO(json.dumps(configuration)).read())
    return encrypted_settings


def decrypt_text(conn, cipher_text):
    return conn['kms'].decrypt(CiphertextBlob=base.b64decode(cipher_text))['Plaintext'].decode()


def encrypt_text(conn, plain_text):
    response = conn['kms'].encrypt(KeyId=conn['encrypt_key_arn'], Plaintext=plain_text)
    cipher_text_blob = response.get('CiphertextBlob')
    return base.b64encode(cipher_text_blob) if cipher_text_blob else plain_text


def conn(encrypt_key_arn):
    return {
        'kms': boto3.client('kms'),
        's3_resource': boto3.resource('s3'),
        's3_client': boto3.client('s3'),
        'encrypt_key_arn': encrypt_key_arn,
    }
