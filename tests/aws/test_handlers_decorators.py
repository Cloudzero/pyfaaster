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

_CONFIG_BUCKET = 'example_config_bucket'


@pytest.fixture(scope='function')
def context(mocker):
    context = attrdict.AttrMap()

    orig_env = os.environ.copy()
    os.environ['NAMESPACE'] = 'test-ns'
    os.environ['CONFIG'] = _CONFIG_BUCKET
    os.environ['ENCRYPT_KEY_ARN'] = 'arn'
    context.os = {'environ': os.environ}

    yield context
    mocker.stopall()
    os.environ = orig_env


def identity_handler(event, context, configuration=None, **kwargs):
    kwargs['configuration'] = configuration['load']() if configuration else None
    response = {
        'body': {
            'event': event,
            'context': context,
            'kwargs': kwargs,
        },
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
    assert utils.deep_get(response, 'body', 'kwargs', 'NAMESPACE') == utils.deep_get(context, 'os', 'environ', 'NAMESPACE')
    assert not utils.deep_get(response, 'body', 'kwargs', 'FOO')


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
    assert utils.deep_get(response, 'body', 'kwargs', 'domain') == domain


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
    assert utils.deep_get(response, 'body', 'kwargs', 'NAMESPACE') == utils.deep_get(context, 'os', 'environ', 'NAMESPACE')


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
        handler = decs.allow_origin_response('.*\.cloudzero\.com')(identity_handler)

        response = handler(event, None)
        assert utils.deep_get(response, 'body', 'kwargs', 'request_origin') == origin
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
        handler = decs.allow_origin_response('.*\.cloudzero\.com')(identity_handler)

        response = handler(event, None)
        assert utils.deep_get(response, 'body', 'kwargs', 'request_origin') == origin
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
    handler = decs.allow_origin_response('.*\.cloudzero\.com')(identity_handler)

    response = handler(event, None)
    assert response.get('statusCode') == 403


@pytest.mark.unit
def test_parameters():
    params = {'a': 1, 'b': 2}
    event = {'queryStringParameters': params}
    handler = decs.parameters(*params.keys())(identity_handler)

    response = handler(event, None)
    response_kwargs = utils.deep_get(response, 'body', 'kwargs')
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
    kwargs_body = utils.deep_get(response, 'body', 'kwargs', 'body')
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
    assert utils.deep_get(response, 'body', 'kwargs', 'sub') == utils.deep_get(event, 'requestContext', 'authorizer', 'sub')


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
def test_http_response():
    event = {'foo': 'bar'}

    handler = decs.http_response(identity_handler)

    response = handler(event, None)
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['event'] == event


@pytest.mark.unit
def test_http_response_with_statusCode():
    event = {'foo': 'bar'}
    handler = decs.http_response(lambda e, c, **kwargs: {'statusCode': 500, 'body': event})
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
    assert response['body']['event'] == event


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
    assert response['body']['event'] == event


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


def test_http_cors_composition(context):

    @decs.allow_origin_response('.*')
    @decs.http_response
    def cors_first(e, c, **ks):
        return {}

    @decs.http_response
    @decs.allow_origin_response('.*')
    def http_first(e, c, **ks):
        return {}

    assert cors_first({}, None) == http_first({}, None)


@pytest.mark.unit
@moto.mock_sts
@moto.mock_sns
def test_publisher(context):
    event = {}
    lambda_context = MockContext('arn:aws:lambda:us-east-1:123456789012')

    messages = {
        'topic-1': 'foo',
        'topic-2': 'bar',
    }
    created_arns = [boto3.client('sns').create_topic(Name=name)['TopicArn'] for name in messages.keys()]

    assert len(created_arns) == 2

    @decs.publisher
    def handler(event, context, **kwargs):
        return {
            'messages': messages
        }

    response = handler(event, lambda_context)
    assert response['messages'] == messages


@pytest.mark.unit
@moto.mock_s3
@moto.mock_kms
@moto.mock_sts
def test_default(context):
    event = {}
    lambda_context = MockContext('::::arn')

    boto3.client('s3').create_bucket(Bucket=_CONFIG_BUCKET)

    handler = decs.default()(identity_handler)

    response = handler(event, lambda_context)
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['event'] == event
    keys = ['account_id', 'client_details', 'CONFIG', 'configuration', 'NAMESPACE']
    print(response_body['kwargs'])
    assert all(k in response_body['kwargs'] for k in keys)
