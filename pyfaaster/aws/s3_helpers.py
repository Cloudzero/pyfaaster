# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Various constructs used to make it easier to use AWS Lambda functions.
"""

import botocore.exceptions as exc

import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


def verify_bucket_access(client, bucket_name):
    """
    Quick and cheap check to see if bucket can be accessed
    Args:
        client: a Boto3 client object
        bucket_name (str): name of bucket to check

    Returns:
        bool: Can we access the bucket?

    """
    try:
        client.head_bucket(Bucket=bucket_name)
        return True
    except exc.ClientError as err:
        logger.debug('Unable to access bucket: {} (error: {})'.format(bucket_name, err))
        return False
