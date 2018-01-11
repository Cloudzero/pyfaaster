# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import base64 as base
import datetime as dt
import io

import boto3
import simplejson as json


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
    decrypted_settings = {k: v.update(value=decrypt_text(conn, v['value'])) if v['encrypted'] else v
                          for k, v in settings.items()}
    return decrypted_settings


def save(conn, config_bucket, config_file, settings):
    encrypted_settings = {k: v.update(value=encrypt_text(conn, v['value'])) if v['encrypted'] else v
                          for k, v in settings.items()}
    configuration = {
        'settings': settings,
        'last_updated': dt.datetime.now(tz=dt.timezone.utc).isoformat(),
    }
    conn['s3_resource'].Object(config_file).put(Body=io.StringIO(json.dumps(configuration)).read())
    return settings


def decrypt_text(conn, cipher_text):
    return conn['kms'].decrypt(CiphertextBlob=base.b64decode(cipher_text))['Plaintext'].decode()


def encrypt_text(conn, plain_text):
    response = conn['kms'].encrypt(KeyId=conn['encrypt_key_arn'], Plaintext=plain_text)
    cipher_text_blob = response.get('CiphertextBlob')
    return base.b64encode(cipher_text_blob) if cipher_text_blob else plain_text


def conn():
    return {
        'kms': boto3.client('kms'),
        's3_resource': boto3.resource('s3'),
        's3_client': boto3.client('s3'),
        'encrypt_key_arn': 'arn:aws:kms:us-east-1:618300337335:key/012ff618-e387-40ee-a472-438f81fecb25',
    }


x = 1
os.environ['AWS_DEFAULT_PROFILE'] = 'cz-dev-core'
conn = {
    'kms': boto3.client('kms'),
    's3_resource': boto3.resource('s3'),
    's3_client': boto3.client('s3'),
    'encrypt_key_arn': 'arn:aws:kms:us-east-1:618300337335:key/012ff618-e387-40ee-a472-438f81fecb25',
}


keys = conn['kms'].list_keys()

settings = load(conn, 'cz-corepipeline-adamcore167-618300337335', 'configuration.json')

new_settings = {**settings, **{'test': {'value': 'foo', 'encrypted': True}}}

s = save(conn, 'cz-corepipeline-adamcore167-618300337335', 'newconf.json', new_settings)




