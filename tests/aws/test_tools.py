# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Unit tests for various AWS-specific utility functions that don't have any connection to domain/business logic
"""

import pytest

import pyfaaster.aws.tools as tools


@pytest.mark.unit
def test_setup_logging():
    """
    Ensure we can setup several logging options without an exception.
    This is kind of a lame test, but rather important as we usually
    call this function on the import of dozens of modules.
    """
    from logging import getLogger, StreamHandler
    from io import StringIO
    log = getLogger('foo')
    log.addHandler(StreamHandler(StringIO()))
    tools.setup_logging('foo')
    tools.setup_logging('bar', level='DEBUG')
