# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.
from collections import namedtuple
import mock

import os
import pytest
import simplejson as json

from pyfaaster.aws.exceptions import HTTPResponseException
import pyfaaster.aws.handlers_decorators_v2 as decs
import pyfaaster.common.utils as utils
from tests.aws.common import MockContext

_CONFIG_BUCKET = 'example_config_bucket'
CONFIG_FILE = 'example_config.json'


@pytest.fixture(scope='function')
def context(mocker):
    context = namedtuple('context', ['os', 'mock_conf'])

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
    @decs.environ_aware(required=['NAMESPACE'], optional=[])
    def handler(e, c, NAMESPACE=None):
        assert NAMESPACE == context.os['environ']['NAMESPACE']

    handler({}, None)


@pytest.mark.unit
def test_environ_aware_opts(context):
    event = {}
    handler = decs.environ_aware(required=[], optional=['NAMESPACE', 'FOO'])(identity_handler)

    response = handler(event, None)
    assert utils.deep_get(response, 'body', 'kwargs', 'NAMESPACE') == context.os['environ']['NAMESPACE']
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

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 500


@pytest.mark.unit
def test_namespace_aware(context):
    event = {}
    handler = decs.namespace_aware(identity_handler)

    response = handler(event, None)
    assert utils.deep_get(response, 'body', 'kwargs', 'NAMESPACE') == context.os['environ']['NAMESPACE']


@pytest.mark.unit
def test_namespace_aware_none():
    event = {}
    handler = decs.namespace_aware(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 500


@pytest.mark.unit
def test_cors_origin_ok(context):
    origins = ['https://app.cloudzero.com', 'https://deeply.nested.subdomain.cloudzero.com']
    for origin in origins:
        event = {
            'headers': {
                'origin': origin
            }
        }
        handler = decs.allow_origin_response(r'.*\.cloudzero\.com')(identity_handler)

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
        handler = decs.allow_origin_response(r'.*\.cloudzero\.com')(identity_handler)

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
    handler = decs.allow_origin_response(r'.*\.cloudzero\.com')(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 403


@pytest.mark.unit
def test_parameters():
    required_qs_params = {'a': 1, 'b': 2}
    optional_qs_params = {'c': 1, 'd': 2}
    all_qs_params = dict()
    all_qs_params.update(**required_qs_params, **optional_qs_params)
    path_params = {'e': 1, 'f': 2}
    event = {
        'queryStringParameters': all_qs_params,
        'pathParameters': path_params,
    }
    handler = decs.parameters(required_querystring=required_qs_params.keys(),
                              optional_querystring=optional_qs_params.keys(),
                              path=path_params.keys()
                              )(identity_handler)

    response = handler(event, None)
    response_kwargs = utils.deep_get(response, 'body', 'kwargs')

    expected_params = dict()
    expected_params.update(**all_qs_params, **path_params)
    assert all([response_kwargs.get(ek) and response_kwargs[ek] == ev for ek, ev in (expected_params.items())])


@pytest.mark.unit
def test_parameters_missing_required_querystring():
    required_qs_params = {'a': 1, 'b': 2}
    optional_qs_params = {'c': 1, 'd': 2}
    path_params = {'e': 1, 'f': 2}
    event = {
        'queryStringParameters': optional_qs_params,
        'pathParameters': path_params,
    }
    handler = decs.parameters(required_querystring=required_qs_params.keys(),
                              optional_querystring=optional_qs_params.keys(),
                              path=path_params.keys()
                              )(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 400
    assert 'Invalid' in excInfo.value.body


@pytest.mark.unit
def test_parameters_missing_optional_querystring():
    required_qs_params = {'a': 1, 'b': 2}
    optional_qs_params = {'c': 1, 'd': 2}
    path_params = {'e': 1, 'f': 2}
    event = {
        'queryStringParameters': required_qs_params,
        'pathParameters': path_params,
    }
    handler = decs.parameters(required_querystring=required_qs_params.keys(),
                              optional_querystring=optional_qs_params.keys(),
                              path=path_params.keys()
                              )(identity_handler)

    response = handler(event, None)
    response_kwargs = utils.deep_get(response, 'body', 'kwargs')

    expected_params = dict()
    expected_params.update(**required_qs_params, **path_params)
    assert all([response_kwargs.get(ek) and response_kwargs[ek] == ev for ek, ev in (expected_params.items())])


@pytest.mark.unit
def test_parameters_missing_path():
    required_qs_params = {'a': 1, 'b': 2}
    optional_qs_params = {'c': 1, 'd': 2}
    path_params = {'e': 1, 'f': 2}
    all_qs_params = dict()
    all_qs_params.update(**required_qs_params, **optional_qs_params)
    event = {
        'queryStringParameters': all_qs_params,
        'pathParameters': {},
    }
    handler = decs.parameters(required_querystring=required_qs_params.keys(),
                              optional_querystring=optional_qs_params.keys(),
                              path=path_params.keys()
                              )(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 400
    assert 'Invalid' in excInfo.value.body


@pytest.mark.unit
def test_body():
    body = {'a': 1, 'b': 2, 'c': 3}
    event = {'body': json.dumps(body)}
    handler = decs.body(required=body.keys())(identity_handler)

    response = handler(event, None)
    kwargs_body = utils.deep_get(response, 'body', 'kwargs', 'body')
    assert all([k in kwargs_body for k in body])


@pytest.mark.unit
def test_body_missing_required_key():
    body = {'a': 1, 'b': 2, 'c': 3}
    event = {'body': json.dumps({k: body[k] for k in ['a', 'b']})}
    handler = decs.body(required=body.keys())(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 400
    assert 'missing required key' in excInfo.value.body


@pytest.mark.unit
def test_body_missing_optional_key():
    body = {'a': 1, 'b': 2, 'c': 3}
    event = {'body': json.dumps({k: body[k] for k in ['a', 'b']})}
    handler = decs.body(optional=body.keys())(identity_handler)

    response = handler(event, None)
    kwargs_body = utils.deep_get(response, 'body', 'kwargs', 'body')
    assert all([k in kwargs_body for k in body])


@pytest.mark.unit
def test_body_json_decode_exception():
    event = {'body': ''}
    handler = decs.body('no_key')(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 400
    assert 'cannot decode json' in excInfo.value.body


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
    assert utils.deep_get(response, 'body', 'kwargs', 'sub') == utils.deep_get(
        event, 'requestContext', 'authorizer', 'sub')


@pytest.mark.unit
def test_sub_aware_none():
    event = {
        'requestContext': {
            'authorizer': {
            },
        },
    }
    handler = decs.sub_aware(identity_handler)

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 500


@pytest.mark.unit
def test_http_response():
    event = {'foo': 'bar'}

    handler = decs.http_response()(identity_handler)

    response = handler(event, None)
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['event'] == event


@pytest.mark.unit
def test_http_response_with_status_code():
    event = {'foo': 'bar'}
    handler = decs.http_response()(lambda e, c, **kwargs: {'statusCode': 500, 'body': event})
    response = handler(event, None)
    assert response['statusCode'] == 500
    assert json.loads(response['body']) == event


@pytest.mark.unit
def test_http_response_with_complex_body():
    input_event = {'a': 1, 'b': {'m', 'n', 'o'}, 'c': {'z': 0}, 'd': [1, '2', True]}
    handler = decs.http_response()(lambda e, c, **kwargs: {'statusCode': 200, 'body': input_event})
    response = handler(input_event, None)
    expected_output = {'a': 1, 'b': ['m', 'n', 'o'], 'c': {'z': 0}, 'd': [1, '2', True]}
    actual_output = json.loads(response['body'])

    # set conversions are not stable
    actual_output['b'] = sorted(actual_output['b'])
    assert actual_output == expected_output
    assert response['statusCode'] == 200


@pytest.mark.unit
def test_http_response_with_default_error_message():
    input_event = {}
    default_error_message = 'Blarg'
    http_response_handler = decs.http_response(default_error_message=default_error_message)
    # lambda w/ *any* exception
    handler = http_response_handler(lambda e, c, **kwargs: 1 / 0)
    response = handler(input_event, MockContext('arn', function_name='foo.my_func'))

    assert response['body'] == default_error_message
    assert response['statusCode'] == 500


@pytest.mark.unit
def test_http_response_with_computed_default_error_message():
    input_event = {}
    function_name = 'foo.my_func'
    http_response_handler = decs.http_response()
    # lambda w/ *any* exception
    handler = http_response_handler(lambda e, c, **kwargs: 1 / 0)
    response = handler(input_event, MockContext('arn', function_name=function_name))

    assert 'my func' in response['body']
    assert response['statusCode'] == 500


@pytest.mark.unit
def test_http_response_with_HTTPResponseException():
    input_event = {}
    expected_statuscode = 403
    expected_body = {'some': 'auth error'}

    def http_exception_handler(e, c, **kwargs):
        raise HTTPResponseException(body=expected_body, statusCode=expected_statuscode)

    # lambda w/ HTTPResponseException
    handler = decs.http_response()(http_exception_handler)
    response = handler(input_event, None)
    actual_output = json.loads(response['body'])

    assert actual_output == expected_body
    assert response['statusCode'] == expected_statuscode


@pytest.mark.unit
def test_http_response_with_pseudo_HTTPResponseException():
    input_event = {}
    expected_statuscode = 420
    expected_body = {'some': 'random error'}

    class myCustomHTTPResponseException(Exception):
        def __init__(self, body, statusCode=500):
            self.body = body
            self.statusCode = statusCode

    def http_exception_handler(e, c, **kwargs):
        raise myCustomHTTPResponseException(body=expected_body, statusCode=expected_statuscode)

    # lambda w/ myCustomHTTPResponseException
    handler = decs.http_response()(http_exception_handler)
    response = handler(input_event, None)
    actual_output = json.loads(response['body'])

    assert actual_output == expected_body
    assert response['statusCode'] == expected_statuscode


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
def test_scopes_type_error():
    class Uncastable():
        def __str__(self):
            raise Exception()

    with pytest.raises(TypeError) as err:
        decs.scopes('foo', Uncastable())
        assert 'castable' in err


@pytest.mark.unit
def test_scopes_type_casting():
    class Castable():
        def __str__(self):
            return 'castable'

    event = {
        'requestContext': {
            'authorizer': {
                'scopes': 'castable',
            }
        }
    }
    handler = decs.scopes(Castable())(identity_handler)

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

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 403
    assert 'insufficient' in excInfo.value.body


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

    with pytest.raises(HTTPResponseException) as excInfo:
        handler(event, None)

    assert excInfo.value.statusCode == 500
    assert 'missing' in excInfo.value.body


@pytest.mark.unit
def test_http_cors_composition(context):
    @decs.allow_origin_response('.*')
    @decs.http_response()
    def cors_first(e, c, **ks):
        return {}

    @decs.http_response()
    @decs.allow_origin_response('.*')
    def http_first(e, c, **ks):
        return {}

    assert cors_first({}, None) == http_first({}, None)


@pytest.mark.unit
def test_subscriber(context):
    lambda_context = MockContext('arn:aws:lambda:us-east-1:123456789012')

    message = {
        'foo': 'bar'
    }

    event = {
        'Records': [
            {
                'Sns': {
                    'TopicArn': 'arn:aws:sns:anything',
                    'Message': json.dumps(message),
                },
            },
        ],
    }

    @decs.subscriber()
    def handler(event, context, message, **kwargs):
        return message

    response = handler(event, lambda_context)
    assert response == message


@pytest.mark.unit
def test_subscriber_required_topic(context):
    lambda_context = MockContext('arn:aws:lambda:us-east-1:123456789012')

    message = {
        'foo': 'bar'
    }

    required_topic_name = 'must-match'

    event = {
        'Records': [
            {
                'Sns': {
                    'TopicArn': f'arn:aws:sns:region:account:namespace-{required_topic_name}',
                    'Message': json.dumps(message),
                },
            },
        ],
    }

    @decs.subscriber(required_topics=['some other name', required_topic_name])
    def handler(event, context, message, **kwargs):
        return message

    response = handler(event, lambda_context)
    assert response == message


@pytest.mark.unit
def test_subscriber_message_body_not_json(context):
    lambda_context = MockContext('arn:aws:lambda:us-east-1:123456789012')

    message = {
        'foo': 'bar'
    }

    required_topic_name = 'must-match'

    event = {
        'Records': [
            {
                'Sns': {
                    'TopicArn': f'arn:aws:sns:region:account:namespace-{required_topic_name}',
                    'Message': message,
                },
            },
        ],
    }

    @decs.subscriber(required_topics=['some other name', required_topic_name])
    def handler(event, context, message, **kwargs):
        return message

    with pytest.raises(Exception) as err:
        handler(event, lambda_context)
    assert 'not decode' in str(err.value)


@pytest.mark.unit
def test_subscriber_event_not_sns_format(context):
    lambda_context = MockContext('arn:aws:lambda:us-east-1:123456789012')

    message = {
        'foo': 'bar'
    }

    event = {
        'message': message
    }

    @decs.subscriber()
    def handler(event, context, message, **kwargs):
        return message

    with pytest.raises(Exception) as err:
        handler(event, lambda_context)
    assert 'Unsupported' in str(err.value)


@pytest.mark.unit
def test_catch_exceptions():
    @decs.catch_exceptions
    def throws_exception():
        raise Exception('Catch meeeeee')

    try:
        throws_exception()
    except Exception:
        pytest.fail("The catch_exceptions decorator didn't do its job! You had one job ... one job!")


@pytest.mark.unit
def test_configuration_aware_lambda_handler(context):
    test_config = {"test": "configuration"}

    @decs.configuration_aware(CONFIG_FILE)
    def handler(event, context, configuration=None):
        assert configuration['load']() == test_config

    with mock.patch("pyfaaster.aws.handlers_decorators_v2.conf") as mock_conf:
        mock_conf.load.return_value = test_config
        handler({}, None)


@pytest.mark.unit
def test_configuration_aware_generic_function(context):
    test_config = {"test": "configuration"}

    @decs.configuration_aware(CONFIG_FILE)
    def handler(*args, **kwargs):
        assert kwargs['configuration']['load']() == test_config

    with mock.patch("pyfaaster.aws.handlers_decorators_v2.conf") as mock_conf:
        mock_conf.load.return_value = test_config
        handler()
        handler('foo', 'bar', {'x': 'y'}, test_arg_1="something", test_arg_2=0)
