# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import logging
import os
import sys


def running_in_aws():
    return bool(os.environ.get('AWS_EXECUTION_ENV'))


def setup_logging(name="DEFAULT_LOGGER", level='INFO'):
    """
    Helper to set up logging consistently across all lambda functions.
    Configures both a named logger and the root logger.

    Args:
        name: (str) - the name of the logger that will be configured along with the root logger
        level: (str) - The log level to use.  Default is INFO.

    Returns:
        Object: Logger object
    """
    __LAMBDA_FORMAT__ = (
        '%(asctime)s.%(msecs)-3d (Z)\t%(aws_request_id)s\t'
        '[%(levelname)-12s]\t%(message)s\n'
    )
    __STANDARD_FORMAT__ = (
        '%(asctime)s.%(msecs)-3d (Z)\t%(name)s\t'
        '[%(levelname)-12s]\t%(message)s\n'
    )
    #
    __DATE_FORMAT__ = '%Y-%m-%d %H:%M:%S'
    __NAME__ = name or os.environ.get('CONFIG') or name

    logger = logging.getLogger(__NAME__)
    if running_in_aws():
        for hand in [h for h in logger.handlers]:
            hand.setFormatter(logging.Formatter(__LAMBDA_FORMAT__, datefmt=__DATE_FORMAT__))
    else:
        for h in logger.handlers:
            logger.removeHandler(h)
        h = logging.StreamHandler(sys.stdout)
        logger.addHandler(h)
        for hand in [h for h in logger.handlers]:
            hand.setFormatter(logging.Formatter(__STANDARD_FORMAT__, datefmt=__DATE_FORMAT__))
    log_level = os.environ.get('LOG_LEVEL', level)
    logger.setLevel(logging.getLevelName(log_level))
    return logger


def get_account_id(context):
    """
    Return the AWS account id for the executing lambda function

    Args:
        context: AWS lambda Context Object http://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns:
        str : AWS Account ID

    """
    return str(context.invoked_function_arn.split(":")[4])


def get_region(context):
    """
    Return the AWS account region for the executing lambda function.

    Args:
        context: AWS lambda Context Object http://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns:
        str : AWS Account Region

    """
    return str(context.invoked_function_arn.split(":")[3])


def get_client_details(event):
    headers = event.get('headers')
    try:
        return {
            "Client": f"{headers.get('User-Agent')}",
            "Source IP": f"{headers.get('X-Forwarded-For')}",
        }
    except (AttributeError, KeyError):
        try:
            # Yes goddamn AWS has a typo in what they return depending on event source
            event_source = str(event['Records'][0].get('eventSource', event['Records'][0].get('EventSource')))
            return event_source or event['Records'][0]
        except (AttributeError, KeyError):
            return event.get('invoked_by') or "invoked"
