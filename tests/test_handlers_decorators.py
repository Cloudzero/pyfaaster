# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import attrdict
import os
import pytest
import simplejson as json

import faaster_aws.handlers_decorators as decs
import faaster_aws.utils as utils


@pytest.fixture(scope='function')
def context(mocker):
    context = attrdict.AttrMap()

    orig_env = os.environ.copy()
    os.environ['NAMESPACE'] = 'test-ns'
    os.environ['CONFIG'] = 'configfile'
    context.os = {'environ': os.environ}

    yield context
    mocker.stopall()
    os.environ = orig_env


def identity_handler(event, context, **kwargs):
    response = {
        'event': event,
        'context': context,
        'kwargs': kwargs,
    }
    return response


@pytest.mark.unit
def test_domain_aware():
    domain = 'test.com'
    event = {
        'requestContext': {
            'authorizer': {
                'domain': domain
            }
        }
    }
    handler = decs.domain_aware(identity_handler)

    response = handler(event, None)
    assert utils.deep_get(response, 'kwargs', 'domain') == domain


@pytest.mark.unit
def test_domain_aware_none():
    event = {}
    handler = decs.domain_aware(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 500


@pytest.mark.unit
def test_namespace_aware(context):
    event = {}
    handler = decs.namespace_aware(identity_handler)

    response = handler(event, None)
    assert utils.deep_get(response, 'kwargs', 'NAMESPACE') == utils.deep_get(context, 'os', 'environ', 'NAMESPACE')


@pytest.mark.unit
def test_namespace_aware_none():
    event = {}
    handler = decs.namespace_aware(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 500


@pytest.mark.unit
def test_cors_origin_ok(context):
    origins = ['https://app.cloudzero.com', 'https://deeply.nested.subdomain.cloudzero.com']
    for origin in origins:
        event = {
            'headers': {
                'origin': origin
            }
        }
        handler = decs.ok_cors_origin('.*\.cloudzero\.com')(identity_handler)

        response = handler(event, None)
        assert utils.deep_get(response, 'kwargs', 'request_origin') == origin
        assert utils.deep_get(response, 'headers', 'Access-Control-Allow-Origin') == origin
        assert utils.deep_get(response, 'headers', 'Access-Control-Allow-Credentials') == 'true'


@pytest.mark.unit
def test_cors_origin_not_case_sensitive(context):
    origins = ['https://app.cloudzero.com', 'https://deeply.nested.subdomain.cloudzero.com']
    for origin in origins:
        event = {
            'headers': {
                'Origin': origin  # CloudFront often rewrites headers and may assign different case like this
            }
        }
        handler = decs.ok_cors_origin('.*\.cloudzero\.com')(identity_handler)

        response = handler(event, None)
        assert utils.deep_get(response, 'kwargs', 'request_origin') == origin
        assert utils.deep_get(response, 'headers', 'Access-Control-Allow-Origin') == origin
        assert utils.deep_get(response, 'headers', 'Access-Control-Allow-Credentials') == 'true'


@pytest.mark.unit
def test_cors_origin_bad():
    origin = 'https://mr.robot.com'
    event = {
        'headers': {
            'origin': origin
        }
    }
    handler = decs.ok_cors_origin('.*\.cloudzero\.com')(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 403


@pytest.mark.unit
def test_parameters():
    params = {'a': 1, 'b': 2}
    event = {'queryStringParameters': params}
    handler = decs.parameters(*params.keys())(identity_handler)

    response = handler(event, None)
    response_kwargs = utils.deep_get(response, 'kwargs')
    assert all([k in response_kwargs for k in params])


@pytest.mark.unit
def test_parameters_bad():
    params = {'a': 1, 'b': 2}
    event = {'queryStringParameters': {}}
    handler = decs.parameters(*params.keys())(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 400


@pytest.mark.unit
def test_body():
    body = {'a': 1, 'b': 2, 'c': 3}
    event = {'body': json.dumps(body)}
    handler = decs.body(*body.keys())(identity_handler)

    response = handler(event, None)
    kwargs_body = utils.deep_get(response, 'kwargs', 'body')
    assert all([k in kwargs_body for k in body])


@pytest.mark.unit
def test_body_missing_required_key():
    body = {'a': 1, 'b': 2, 'c': 3}
    event = {'body': json.dumps({k: body[k] for k in ['a', 'b']})}
    handler = decs.body(*body.keys())(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 400
    assert 'missing required key' in response.get('body')


@pytest.mark.unit
def test_body_json_decode_exception():
    event = {'body': ''}
    handler = decs.body('no_key')(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 400
    assert 'cannot decode json' in response.get('body')


@pytest.mark.unit
def test_scopes():
    event = {
        'requestContext': {
            'authorizer': {
                'scopes': 'read write',
            }
        }
    }
    handler = decs.scopes('read', 'write')(identity_handler)

    response = handler(event, None)
    assert response['event'] == event


@pytest.mark.unit
def test_insufficient_scopes():
    event = {
        'requestContext': {
            'authorizer': {
                'scopes': 'read write',
            }
        }
    }
    handler = decs.scopes('read', 'write', 'admin')(identity_handler)

    response = handler(event, None)
    assert response['statusCode'] == 403
    assert 'insufficient' in response['body']


@pytest.mark.unit
def test_no_scopes():
    event = {
        'requestContext': {
            'authorizer': {
                'scopes': 'read write',
            }
        }
    }
    handler = decs.scopes()(identity_handler)

    response = handler(event, None)
    assert response['event'] == event


@pytest.mark.unit
def test_no_scopes_in_context():
    event = {
        'requestContext': {
            'authorizer': {
            }
        }
    }
    handler = decs.scopes()(identity_handler)

    response = handler(event, None)
    assert response['statusCode'] == 500
    assert 'missing' in response['body']


class MockContext:
    def __init__(self, farn):
        self.invoked_function_arn = farn


@pytest.mark.unit
def test_default(context):
    event = {}
    context = MockContext('::::arn')
    handler = decs.default(False)(identity_handler)

    response = handler(event, context)
    assert response['statusCode'] == 500
    assert 'missing' in response['body']
