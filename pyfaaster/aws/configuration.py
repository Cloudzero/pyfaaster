# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import base64 as base
import datetime as dt
import functools
import io

import boto3
import simplejson as json

import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


def load(conn, config_bucket, config_file):
    logger.info(f'Reading configuration from {config_bucket}/{config_file}.')
    content_object = conn['s3_client'].get_object(Bucket=config_bucket, Key=config_file)
    file_content = content_object['Body'].read().decode('utf-8')

    loaded_configuration = json.loads(file_content)
    settings = loaded_configuration.get('settings', {})
    return decrypt_settings(conn, settings)


def save(conn, config_bucket, config_file, settings):
    logger.info(f'Saving configuration to {config_bucket}/{config_file}.')
    encrypted_settings = encrypt_settings(conn, settings)
    configuration = {
        'settings': encrypted_settings,
        'last_updated': dt.datetime.now(tz=dt.timezone.utc).isoformat(),
    }
    conn['s3_resource'].Object(config_bucket, config_file).put(Body=io.StringIO(json.dumps(configuration)).read())
    return encrypted_settings


def crypt_settings(crypt_fn, settings):
    return {k: {**v, **{'value': crypt_fn(v['value'])}} if v['encrypted'] else v
            for k, v in settings.items()}


def encrypt_settings(conn, settings):
    return crypt_settings(functools.partial(encrypt_text, conn), settings) if conn['encrypt_key_arn'] else settings


def decrypt_settings(conn, settings):
    return crypt_settings(functools.partial(decrypt_text, conn), settings) if conn['encrypt_key_arn'] else settings


def decrypt_text(conn, cipher_text):
    response = conn['kms'].decrypt(CiphertextBlob=base.b64decode(cipher_text))
    plain_text = response.get('Plaintext')
    return plain_text.decode() if plain_text else cipher_text


def encrypt_text(conn, plain_text):
    response = conn['kms'].encrypt(KeyId=conn['encrypt_key_arn'], Plaintext=plain_text)
    cipher_text_blob = response.get('CiphertextBlob')
    return base.b64encode(cipher_text_blob) if cipher_text_blob else plain_text


def load_or_create(conn, config_bucket, config_file):
    try:
        logger.info(f'Attempting to load {config_bucket}/{config_file}')
        return load(conn, config_bucket, config_file)
    except Exception as error:
        logger.info(f'Failed to load, attempting to create {config_bucket}/{config_file}')
        return save(conn, config_bucket, config_file, {})


def conn(encrypt_key_arn):
    return {
        'kms': boto3.client('kms'),
        's3_resource': boto3.resource('s3'),
        's3_client': boto3.client('s3'),
        'encrypt_key_arn': encrypt_key_arn,
    }


@functools.lru_cache(maxsize=8)
def read_only(config_bucket, config_file, encrypt_key_arn=None):
    logger.info(f'Reading {config_bucket}/{config_file}.')
    connection = conn(encrypt_key_arn)
    return load(connection, config_bucket, config_file)
