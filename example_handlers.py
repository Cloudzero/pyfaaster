# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import pyfaaster.aws.handlers_decorators as decs


@decs.default()
def hello_world(event, context, **kwargs):
    return {
        'statusCode': 200,
        'body': 'Hello, World!'
    }
