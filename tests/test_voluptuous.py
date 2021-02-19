# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import pytest
from voluptuous import Maybe


def validator_that_raises_typeerror(x):
    if x is None:
        raise TypeError('Voluptuous 0.12.1 has a bug where Maybe(validator) checks the validator first.')
    return x


@pytest.mark.unit
def test_voluptuous_maybe_checks_none_first():
    schema = Maybe(validator_that_raises_typeerror)
    assert schema(None) is None
