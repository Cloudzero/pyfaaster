# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Various general utility functions that don't have any connection to domain/business logic
"""

import functools
import uuid
import enum
import simplejson as json


def deep_get(dictionary, *keys, ignore_case=False):
    """
    Safely get nested keys out of dictionary.

    E.g.,
    >>> d = {'foo': {'bar': 'baz'}}
    >>> deep_get(d, 'foo', 'bar')
    'baz'
    >>> deep_get(d, 'foo', 'BLARG')
    None

    Args:
        dictionary (dict): dictionary to get
        keys (*args): list of positional args containing keys
        ignore_case: bool - if True, and a key is a string, ignore case. Defaults to False.

    Returns:
        value at given key if path exists; None otherwise
    """
    try:
        # We can handle different inputs as long as they are dict-like
        dictionary.items()
        dictionary.get('')
    except AttributeError:
        return None

    def reducer(d, k):
        if not d:
            return None
        search_key = k.lower() if ignore_case and isinstance(k, str) else k
        working_dict = {k.lower() if isinstance(k, str) else k: v for k, v in d.items()} if ignore_case else d
        return working_dict.get(search_key)

    return functools.reduce(reducer, keys, dictionary)


def select_keys(dictionary, *keys):
    """
    Safely get a 'subset' of a dictionary. Ignore `keys` that don't exist in dictionary.

    E.g.,
    >>> import pyfaaster.aws.utils as utils
    >>> d = {'a': 1, 'b': 2, 'c': 3}
    >>> utils.select_keys(d, 'a')
    {'a': 1}
    >>> utils.select_keys(d, 'a', 'b')
    {'b': 2, 'a': 1}
    >>> utils.select_keys(d, 'a', 'unknown_key')
    {'a': 1}
    >>> utils.select_keys({})
    {}
    >>> utils.select_keys({'a': 1})
    {}

    Args:
        dictionary (dict): dictionary to get
        keys (*args): list of keys

    Returns:
        dictionary (dict): dictionary subset with just the given `keys` and their values
    """
    try:
        # We can handle different inputs as long as they are dict-like
        dictionary.items()
        dictionary.get('')
    except AttributeError:
        return None

    return {k: dictionary[k]
            for k in dictionary.keys() & set(keys)}


def sanitize_passwords(input_settings):
    return {k: '********' if 'password' in k else v for k, v in input_settings.items()}


def load_and_render_template(directory, file_name, **kwargs):
    with open(f'{directory}/{file_name}', 'r') as f:
        template_file = f.read()
        return template_file.format(**kwargs)


def create_id() -> str:
    """
    Create a unique ID, UUIDv4 style

    Returns:
        str:
    """
    return str(uuid.uuid4())


class EnumEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, enum.Enum):
            return o.value
        return super(EnumEncoder, self).default(o)
