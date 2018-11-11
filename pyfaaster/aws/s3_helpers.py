# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Various constructs used to make it easier to use AWS Lambda functions.
"""

import botocore.exceptions
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
    except botocore.exceptions.ClientError as err:
        logger.debug('Unable to access bucket: {} (error: {})'.format(bucket_name, err))
        return False


def verify_bucket_read(client, bucket, prefix=None):
    """
    Verify that we can read a file from a given S3 bucket. Since the only way to truly ensure we have read rights
    is to actually read a file, that's what we attempt to do. However, in some cases we might be testing an empty
    bucket, in which case we can't be 100% sure we have read rights, so in those cases we return 'maybe'
    Args:
        client: Boto3 client object
        bucket (str): The bucket
        prefix (str): A key path

    Returns:
        str

    """
    prefix_string = '/' + prefix if prefix else ''
    result = "no"

    if not bucket:
        return result

    try:
        client.head_bucket(Bucket=bucket)
        if prefix:
            response = client.list_objects_v2(Bucket=bucket, Prefix=prefix_string)
        else:
            response = client.list_objects_v2(Bucket=bucket)

        objects = response.get('Contents', {})
        for obj in objects:
            # Iterate over objects, use size to quickly determine if object is a file (not a folder)
            if obj.get('Size'):
                try:
                    # get object will fail if storage class is Glacier
                    response = client.get_object(Bucket=bucket, Key=obj.get('Key'), Range='0')
                    if response.get('ContentLength'):
                        result = "yes"
                        break
                except botocore.exceptions.ClientError as err:
                    if "The operation is not valid for the object's storage class" in str(err):
                        # Bucket has mixed storage classes that block reading (e.g. Glacier), but permissions look ok
                        result = "yes"
                        logger.debug('Readable file found in bucket {}, '
                                     'but could not load due to storage class. ({})'.format(bucket, err))
                    else:
                        # No permissions
                        result = "no"
                        logger.debug('Could list objects in bucket {} but could not read any files'
                                     '({})'.format(bucket, err))
                    break
        else:
            result = "maybe"
    except botocore.exceptions.ClientError as err:
        logger.debug('Unable to access bucket: {} (error: {})'.format(bucket, err))
        result = "no"

    return result
