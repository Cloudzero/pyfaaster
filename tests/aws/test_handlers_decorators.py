# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.


import attrdict
import boto3
import moto
import os
import pytest
import simplejson as json

import pyfaaster.aws.handlers_decorators as decs
import pyfaaster.aws.utils as utils


@pytest.fixture(scope='function')
def context(mocker):
    context = attrdict.AttrMap()

    orig_env = os.environ.copy()
    os.environ['NAMESPACE'] = 'test-ns'
    os.environ['CONFIG'] = 'config_bucket'
    os.environ['ENCRYPT_KEY_ARN'] = 'arn'
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
def test_environ_aware_named_kwargs(context):
    @decs.environ_aware(['NAMESPACE'], [])
    def handler(e, c, NAMESPACE=None):
        assert NAMESPACE == utils.deep_get(context, 'os', 'environ', 'NAMESPACE')

    handler({}, None)


@pytest.mark.unit
def test_environ_aware_opts():
    event = {}
    handler = decs.environ_aware([], ['NAMESPACE', 'FOO'])(identity_handler)

    response = handler(event, None)
    assert utils.deep_get(response, 'kwargs', 'NAMESPACE') == utils.deep_get(context, 'os', 'environ', 'NAMESPACE')
    assert not utils.deep_get(response, 'kwargs', 'FOO')


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
def test_sub_aware():
    event = {
        'requestContext': {
            'authorizer': {
                'sub': 'uuid',
            },
        },
    }
    handler = decs.sub_aware(identity_handler)

    response = handler(event, None)
    assert utils.deep_get(response, 'kwargs', 'sub') == utils.deep_get(event, 'requestContext', 'authorizer', 'sub')


@pytest.mark.unit
def test_sub_aware_none():
    event = {
        'requestContext': {
            'authorizer': {
            },
        },
    }
    handler = decs.sub_aware(identity_handler)

    response = handler(event, None)
    assert response['statusCode'] == 500


@pytest.mark.unit
def test_apig_response():
    event = {'foo': 'bar'}
    handler = decs.apig_response(identity_handler)
    response = handler(event, None)
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['event'] == event


@pytest.mark.unit
def test_apig_response_with_statusCode():
    event = {'foo': 'bar'}
    handler = decs.apig_response(lambda e, c, **kwargs: {'statusCode': 500, 'body': event})
    response = handler(event, None)
    assert response['statusCode'] == 500
    assert json.loads(response['body']) == event


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


class MockContext(dict):
    def __init__(self, farn):
        self.invoked_function_arn = farn
        dict.__init__(self, invoked_function_arn=farn)


@pytest.mark.integration
@moto.mock_s3
@moto.mock_kms
@moto.mock_sts
def test_default(context):
    event = {}
    lambda_context = MockContext('::::arn')
    handler = decs.default()(identity_handler)

    boto3.client('s3').create_bucket(Bucket=utils.deep_get(context, 'os', 'environ', 'CONFIG'))

    response = handler(event, lambda_context)
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['event'] == event
    keys = ['account_id', 'client_details', 'CONFIG', 'configuration', 'NAMESPACE']
    assert all(k in response_body['kwargs'] for k in keys)
