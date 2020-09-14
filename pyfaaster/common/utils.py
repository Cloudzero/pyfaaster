# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

"""
Various general utility functions that don't have any connection to domain/business logic
"""
import collections
import functools
import itertools
import uuid
import enum
import simplejson as json
import random
import string


def deep_get(dictionary, *keys, ignore_case=False):
    """
    Safely get nested keys out of dictionary.

    E.g.,
    >>> d = {'foo': {'bar': 'baz'}}
    >>> deep_get(d, 'foo', 'bar')
    'baz'
    >>> deep_get(d, 'foo', 'BLARG')


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
    >>> d = {'a': 1, 'b': 2, 'c': 3}
    >>> select_keys(d, 'a')
    {'a': 1}
    >>> select_keys(d, 'a', 'b')
    {'a': 1, 'b': 2}
    >>> select_keys(d, 'a', 'unknown_key')
    {'a': 1}
    >>> select_keys({})
    {}
    >>> select_keys({'a': 1})
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

    return dict(collections.OrderedDict({k: v for k, v in dictionary.items() if k in set(keys)}))


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


def create_random_string(size=12, chars=string.ascii_letters + string.digits):
    """
    Generate a cryptographically strong random string
    http://stackoverflow.com/a/2257449/771901

    Args:
        size (int): length of string to generate
        chars (str): set of digits that will be used to generate the string

    Returns:
        str: Generated random string
    """
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))


def one(iter):
    """ Returns True if exactly one member of iter has a truthy value, else False.

    Args:
        iter (iterable): an iterable containing values that can be evaluated as bools.

    Returns:
        (bool): True if exactly one member is truthy, else False.

    >>> one({"a", None, True})
    False

    >>> one({None, None, None})
    False

    >>> one({True, False, False})
    True

    >>> one({False, False, True})
    True
    """
    return len([s for s in iter if s]) == 1


def is_json(input):
    try:
        _ = json.loads(input)  # noqa: F841
    except ValueError:
        return False
    return True


def group_by(xs, fx, fys=lambda ys: ys):
    """ Returns a dictionary of the elements of `xs` keyed by the result of
        `fx` on each element. The value at each key will be a list of the
        corresponding elements, in the order they appeared in `xs`, the optional
        `fys` transforms this list of elements, i.e. it expects a list as its arg.
    >>> xs = [['a', 1], ['b', 2], ['c', 3], ['a', 2]]
    >>> group_by(xs, lambda x: x[0])
    defaultdict(<class 'list'>, {'a': [['a', 1], ['a', 2]], 'b': [['b', 2]], 'c': [['c', 3]]})
    >>> group_by(xs, lambda x: x[0], fys=lambda ys: [y[1] for y in ys])
    defaultdict(<class 'list'>, {'a': [1, 2], 'b': [2], 'c': [3]})
    """
    groups = collections.defaultdict(list)
    for k, ys in itertools.groupby(sorted(xs, key=fx), key=fx):
        groups[k].extend(fys(list(ys)))
    return groups
