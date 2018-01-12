# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import pyfaaster.aws.decorators as decs


@decs.lambda_handler()
def example__hello_world(event, context, namespace, configuration, client_details):
    return {
        'statusCode': 200,
        'body': 'Hello, World!'
    }
