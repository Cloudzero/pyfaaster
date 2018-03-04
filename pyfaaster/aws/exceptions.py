# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


class HTTPResponseException(Exception):
    """Exception for passing special response body to http_response decorator. The given
    `body` will be json serialized before returning it."""

    def __init__(self, body):
        self.body = body
