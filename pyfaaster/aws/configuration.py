# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import functools
import io

import boto3
import simplejson as json

import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


def load(conn, config_bucket, config_file):
    logger.info(f'Reading configuration from {config_bucket}/{config_file}.')
    content_object = conn['session'].client('s3').get_object(Bucket=config_bucket, Key=config_file)
    file_content = content_object['Body'].read().decode('utf-8')

    settings = json.loads(file_content)
    logger.debug(f'loaded settings')
    return settings


def save(conn, config_bucket, config_file, settings):
    logger.info(f'Saving configuration to {config_bucket}/{config_file}.')
    conn['session'].client('s3').put_object(Bucket=config_bucket,
                                            Key=config_file,
                                            Body=io.StringIO(json.dumps(settings)).read(),
                                            ServerSideEncryption='aws:kms',
                                            SSEKMSKeyId=conn['encrypt_key_arn'])
    return settings


def load_or_create(conn, config_bucket, config_file):
    try:
        logger.info(f'Attempting to load {config_bucket}/{config_file}')
        return load(conn, config_bucket, config_file)
    except Exception as error:
        logger.info(f'Failed to load, attempting to create {config_bucket}/{config_file}')
        return save(conn, config_bucket, config_file, {})


def conn(encrypt_key_arn):
    return {
        'session': boto3.session.Session(),
        'encrypt_key_arn': encrypt_key_arn,
    }


@functools.lru_cache(maxsize=8)
def read_only(config_bucket, config_file):
    logger.info(f'Reading {config_bucket}/{config_file}.')
    connection = conn(None)
    return load(connection, config_bucket, config_file)
