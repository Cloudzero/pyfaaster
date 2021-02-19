# Copyright (c) 2020 CloudZero - ALL RIGHTS RESERVED - PROPRIETARY AND CONFIDENTIAL
# Unauthorized copying of this file and/or project, via any medium is strictly prohibited.
# Direct all questions to legal@cloudzero.com

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
