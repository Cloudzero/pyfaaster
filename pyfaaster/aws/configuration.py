# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

from cachetools import cached, LRUCache
from cachetools.keys import hashkey
import io

import boto3
import simplejson as json

import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


def load(conn, config_bucket, config_file):
    logger.info(f'Reading configuration from {config_bucket}/{config_file}.')
    content_object = conn['client'].get_object(Bucket=config_bucket, Key=config_file)
    file_content = content_object['Body'].read().decode('utf-8')

    settings = json.loads(file_content)
    logger.debug('loaded settings')
    return settings


def save(conn, config_bucket, config_file, settings):
    logger.info(f'Saving configuration to {config_bucket}/{config_file}.')
    encryption = {'ServerSideEncryption': 'aws:kms', 'SSEKMSKeyId': conn['encrypt_key_arn']} if conn[
        'encrypt_key_arn'] else {'ServerSideEncryption': 'AES256'}
    conn['client'].put_object(Bucket=config_bucket,
                              Key=config_file,
                              Body=io.StringIO(json.dumps(settings)).read(),
                              **encryption)
    return settings


def load_or_create(conn, config_bucket, config_file):
    try:
        logger.info(f'Attempting to load {config_bucket}/{config_file}')
        return load(conn, config_bucket, config_file)
    except Exception as error:
        logger.info(f'Failed to load, attempting to create {config_bucket}/{config_file} ({error}')
        return save(conn, config_bucket, config_file, {})


def conn(encrypt_key_arn=None, client=None):
    return {
        'client': client or boto3.client('s3'),
        'encrypt_key_arn': encrypt_key_arn,
    }


read_only_cache = LRUCache(maxsize=32)


@cached(cache=read_only_cache,
        key=lambda conn, config_bucket, config_file: hashkey(config_bucket, config_file))
def read_only(conn, config_bucket, config_file):
    logger.info(f'Reading {config_bucket}/{config_file}.')
    return load(conn, config_bucket, config_file)
