# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Unit tests for various general utility functions that don't have any connection to domain/business logic
"""

import enum
import pytest
import simplejson as json

import pyfaaster.common.utils as utils


@pytest.mark.unit
def test_deep_get_exact_match():
    input_dict = {
        'foo': {
            '123': 'abc',
            '456': 'def'
        },
        'bar': {
            '789': 'ghi',
            '012': 'jkl'
        },
        'baz': {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 'baz', '345')
    assert 'mno' == result
    result = utils.deep_get(input_dict, 'foo')
    assert {'123': 'abc', '456': 'def'} == result
    result = utils.deep_get(input_dict, 'BaR', '012')
    assert result is None


@pytest.mark.unit
def test_deep_get_case_insensitive_match():
    input_dict = {
        'foo': {
            '123': 'abc',
            '456': 'def',
            'AAA': {
                'BBB': '919'
            }
        },
        'bar': {
            '789': 'ghi',
            '012': 'jkl'
        },
        'bAz': {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 'BaR', '012', ignore_case=True)
    assert 'jkl' == result
    result = utils.deep_get(input_dict, 'bar', '012', ignore_case=True)
    assert 'jkl' == result
    result = utils.deep_get(input_dict, 'baz', '345', ignore_case=True)
    assert 'mno' == result
    result = utils.deep_get(input_dict, 'FOO', 'aAa', 'BbB', ignore_case=True)
    assert '919' == result
    result = utils.deep_get(input_dict, 'BaR', '012', ignore_case=False)
    assert result is None
    result = utils.deep_get(input_dict, 'bar', '012', ignore_case=False)
    assert 'jkl' == result


@pytest.mark.unit
def test_deep_get_case_mixed_keys():
    input_dict = {
        frozenset({1, 2, 3}): {
            123: 'abc',
            456.9: 'def'
        },
        123: {
            (3, 4): 'ghi',
            (5, 6): 'jkl'
        },
        (1, 2): {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 123, (5, 6), ignore_case=True)
    assert 'jkl' == result
    result = utils.deep_get(input_dict, (1, 2), '678', ignore_case=False)
    assert 'pqr' == result
    result = utils.deep_get(input_dict, frozenset({1, 2, 3}), 456.9)
    assert 'def' == result


@pytest.mark.unit
def test_deep_get_bad_input():
    result = utils.deep_get(None, 'foo', '012')
    assert result is None
    result = utils.deep_get([], 'foo', '012')
    assert result is None


@pytest.mark.unit
def test_deep_get_identity_input():
    result = utils.deep_get({'foo': 'bar'})
    assert result == {'foo': 'bar'}


@pytest.mark.unit
def test_deep_get_no_match():
    input_dict = {
        'foo': {
            '123': 'abc',
            '456': 'def'
        },
        'bar': {
            '789': 'ghi',
            '012': 'jkl'
        },
        'baz': {
            '345': 'mno',
            '678': 'pqr'
        }
    }
    result = utils.deep_get(input_dict, 'bar', 'aaa')
    assert result is None
    result = utils.deep_get(input_dict, 'foobar')
    assert result is None
    result = utils.deep_get(input_dict, None)
    assert result is None


@pytest.mark.unit
def test_select_keys_one():
    input_dict = {
        'a': 1,
        'b': 2,
        'c': 3,
    }
    result = utils.select_keys(input_dict, 'a')
    assert result['a'] == input_dict['a']
    assert 'b' not in result and 'c' not in result


@pytest.mark.unit
def test_select_keys_all():
    input_dict = {
        'a': 1,
        'b': 2,
        'c': 3,
    }
    result = utils.select_keys(input_dict, *input_dict.keys())
    assert result == input_dict


@pytest.mark.unit
def test_select_keys_missing():
    input_dict = {
        'a': 1,
        'b': 2,
        'c': 3,
    }
    result = utils.select_keys(input_dict, *(list(input_dict.keys()) + ['bad_key']))
    assert result == input_dict


@pytest.mark.unit
def test_select_keys_none():
    assert utils.select_keys({}) == {}
    assert utils.select_keys({'a': 1}) == {}
    assert utils.select_keys(None, 'a') is None


@pytest.mark.unit
def test_enum_json_encoder():
    class SampleEnum(enum.Enum):
        NOT_OK = 0
        OK = 1
        MAYBE_OK = 2

    payload = {'key': SampleEnum.OK}
    result = json.dumps(payload, cls=utils.EnumEncoder)
    assert result
    result = json.loads(result)
    assert result['key'] == SampleEnum.OK.value


@pytest.mark.unit
def test_group_by():
    xs = [['a', 1], ['b', 2], ['c', 3], ['a', 2]]
    assert utils.group_by(xs, lambda x: x[0]) == {'a': [['a', 1], ['a', 2]], 'b': [['b', 2]], 'c': [['c', 3]]}
    assert utils.group_by(xs, lambda x: x[0], fys=lambda ys: [y[1] for y in ys]) == {'a': [1, 2], 'b': [2], 'c': [3]}
