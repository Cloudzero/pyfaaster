# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import functools


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
