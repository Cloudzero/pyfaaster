# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


class MockContext(dict):
    def __init__(self, farn, function_name=None):
        self.invoked_function_arn = farn
        self.function_name = function_name
        dict.__init__(self, invoked_function_arn=farn, function_name=function_name)
