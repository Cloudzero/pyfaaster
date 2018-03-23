# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Various constructs used to make it easier to use AWS Lambda functions.
"""

import boto3
import pyfaaster.aws.tools as tools

logger = tools.setup_logging('pyfaaster')


class LambdaNotFoundException(Exception):
    pass


class LambdaInvokeException(Exception):
    def __init__(self, messages, boto_error) -> None:
        super().__init__(messages, boto_error)
        self.inner_error = boto_error


def lambda_invoke(namespace, base_func_name, func_prefix='', payload=bytes(), run_async=False):
    """
    Invoke a lambda function

    Args:
        namespace (str): The identifier of this installation
        base_func_name (str): The base name of the lambda function to invoke
        func_prefix (str): A prefix to assign to the function name (can denote something like an application name)
        payload: The payload to send to the lambda function.  Default is an empty set of bytes.
        run_async (bool): If true, invoke the lambda in a non-blocking fire-and-forget manner.  If false, the
                          caller will wait for a response before continuing.

    Returns:
        The response from the lambda.  When using async mode, a response will be available, but it will
        never contain any output - just success/failure of delivery.
    """
    lambda_client = boto3.client('lambda')

    template = '{pref}-{namespace}-{name}'
    full_name = template.format(pref=func_prefix, namespace=namespace, name=base_func_name)

    try:
        invoke_type = 'Event' if run_async else 'RequestResponse'
        synchronicity = 'asynchronously' if run_async else 'synchronously'
        logger.debug(f'Invoking {full_name} {synchronicity} and sending {len(payload)} bytes')
        return_value = lambda_client.invoke(FunctionName=full_name, Payload=payload, InvocationType=invoke_type)
    except lambda_client.exceptions.ResourceNotFoundException:
        raise LambdaNotFoundException(f'Lambda {full_name} was called, but does not exist')
    except Exception as err:
        raise LambdaInvokeException('Error calling lambda', err)
    return return_value
