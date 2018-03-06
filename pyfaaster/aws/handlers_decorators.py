# -*- coding: utf-8 -*-
# Copyright (c) 2016-present, CloudZero, Inc. All rights reserved.
# Licensed under the BSD-style license. See LICENSE file in the project root for full license information.

import functools
import re
import os

import simplejson as json

import pyfaaster.aws.configuration as conf
from pyfaaster.aws.exceptions import HTTPResponseException
import pyfaaster.aws.publish as publish
import pyfaaster.aws.tools as tools
import pyfaaster.aws.utils as utils


logger = tools.setup_logging('pyfaaster')


def environ_aware(required=None, optional=None, **kwargs):
    """ Decorator that will add each environment variable in reqs and opts
    to the handler kwargs. The variables in reqs will be checked for existence
    and return immediately if the environmental variable is missing.

    Args:
        required (iterable): required environment vars
        optional (iterable): optional environment vars

    Returns:
        handler (func): a lambda handler function that is environ aware
    """
    def environ_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            for r in required if required else {}:
                value = os.environ.get(r)
                if not value:
                    logger.error(f'{r} environment variable missing.')
                    return {'statusCode': 500, 'body': f'Invalid {r}.'}
                kwargs[r] = value

            for o in optional if optional else {}:
                kwargs[o] = os.environ.get(o)

            return handler(event, context, **kwargs)

        return handler_wrapper

    return environ_handler


namespace_aware = environ_aware(['NAMESPACE'], [])


def domain_aware(handler):
    """ Decorator that will check and add event.requestContext.authorizer.domain to the event kwargs.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a lambda handler function that is domain aware
    """
    def handler_wrapper(event, context, **kwargs):
        domain = utils.deep_get(event, 'requestContext', 'authorizer', 'domain')
        if not domain:
            logger.error('Domain requestContext variable missing.')
            return {'statusCode': 500, 'body': 'Invalid domain.'}

        kwargs['domain'] = domain
        return handler(event, context, **kwargs)

    return handler_wrapper


def allow_origin_response(*origins):
    """ Decorator that will check that the event.headers.origin is in origins; if the origin
    is valid, this decorator will add it to the response headers.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a lambda handler function that is authorized
    """
    def allow_origin_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            logger.debug(f'Checking origin for event: {event}')

            # Check Origin
            request_origin = utils.deep_get(event, 'headers', 'origin', ignore_case=True)
            if not any(re.match(o, str(request_origin)) for o in origins):
                logger.warning(f'Invalid request origin: {request_origin}')
                return {'statusCode': 403, 'body': 'Unknown origin.'}

            # call handler
            kwargs['request_origin'] = request_origin
            response = handler(event, context, **kwargs)

            if not isinstance(response, dict):
                raise Exception(
                    f'Unsupported response type {type(response)}; response must be dict for *_response decorators.')

            # add origin to response headers
            current_headers = response.get('headers', {})
            cors_headers = {'Access-Control-Allow-Origin': request_origin,
                            'Access-Control-Allow-Credentials': 'true'}
            response['headers'] = {**current_headers, **cors_headers}
            return response

        return handler_wrapper

    return allow_origin_handler


def parameters(required_querystring=None, optional_querystring=None, path=None):
    """ Decorator that will check and add queryStringParameters
        and pathParameters to the event kwargs.

    Args:
        required_querystring (iterable): Required queryStringParameters
        optional_querystring (iterable): Optional queryStringParameters
        path (iterable): pathParameters (these are always required)

    Returns:
        handler (func): a lambda handler function that is namespace aware
    """
    def parameters_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            for param in required_querystring if required_querystring else {}:
                value = utils.deep_get(event, 'queryStringParameters', param)
                if not value:
                    logger.error(f'queryStringParameter [{param}] missing from event [{event}].')
                    return {'statusCode': 400, 'body': f'Invalid {param}.'}
                kwargs[param] = value
            for param in optional_querystring if optional_querystring else {}:
                value = utils.deep_get(event, 'queryStringParameters', param)
                if value:
                    kwargs[param] = value
            for param in path if path else {}:
                value = utils.deep_get(event, 'pathParameters', param)
                if not value:
                    logger.error(f'pathParameter [{param}] missing from event [{event}].')
                    return {'statusCode': 400, 'body': f'Invalid {param}.'}
                kwargs[param] = value
            return handler(event, context, **kwargs)

        return handler_wrapper

    return parameters_handler


def body(required=None, optional=None):
    """ Decorator that will check that event.get('body') has keys, then add a map of selected keys
    to kwargs.

    Args:
        required (iterable): Required body keys
        optional (iterable): Optional body keys

    Returns:
        handler (func): a lambda handler function that is namespace aware
    """
    def body_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            try:
                event_body = json.loads(event.get('body'))
            except json.JSONDecodeError as err:
                return {'statusCode': 400, 'body': 'Invalid event.body: cannot decode json.'}

            body_required = {k: event_body.get(k) for k in (required if required else {})}
            if not all((v is not None for v in body_required.values())):
                logger.error(f'There is a required key in [{required}] missing from event.body [{event_body}].')
                return {'statusCode': 400, 'body': 'Invalid event.body: missing required key.'}

            body_optional = {k: event_body.get(k) for k in (optional if optional else {})}

            handler_body = {}
            handler_body.update(**body_required, **body_optional)
            kwargs['body'] = handler_body

            return handler(event, context, **kwargs)

        return handler_wrapper

    return body_handler


def scopes(*scopeList):
    """ Decorator that will check that event.requestContext.authorizer.scopes has the given
    scopes. This decorator assumes that you have an upstream authorizer putting the scopes from the
    access_token into the event.requestContext.authorizer.scopes. This is a reasonable assumption
    if you are using a custom authorizer, which we are!

    Args:
        scopeList (List): List of required access_token scopes.

    Returns:
        handler (func): a lambda handler function that is namespace aware
    """
    def scopes_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            token_scopes = utils.deep_get(event, 'requestContext', 'authorizer', 'scopes')

            if not token_scopes:
                return {'statusCode': 500, 'body': 'Invalid token scopes: missing!'}

            if not all((s in token_scopes for s in scopeList)):
                logger.warning(f'There is a required scope [{scopeList}] missing from token scopes [{token_scopes}].')
                return {'statusCode': 403, 'body': 'access_token has insufficient access.'}

            return handler(event, context, **kwargs)

        return handler_wrapper

    return scopes_handler


def sub_aware(handler):
    """ Decorator that will check and add event.requestContext.authorizer.sub to the event kwargs.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a lambda handler function that is sub aware
    """
    def handler_wrapper(event, context, **kwargs):
        sub = utils.deep_get(event, 'requestContext', 'authorizer', 'sub')
        if not sub:
            logger.error('Sub requestContext variable missing.')
            return {'statusCode': 500, 'body': 'Invalid sub.'}

        kwargs['sub'] = sub
        return handler(event, context, **kwargs)

    return handler_wrapper


def http_response(default_error_message=None):
    """ Decorator that will wrap handler response in an API Gateway compatible dict with
    statusCode and json serialized body. If handler result has a 'body', this decorator
    will serialize it into the API Gateway body; if the handler result does _not_ have a
    body, this decorator will return statusCode 200 and serialize the entire result.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a lambda handler function that whose result is HTTPGateway compatible.
    """
    def http_response_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            try:
                res = handler(event, context, **kwargs)
                if not isinstance(res, dict):
                    raise Exception(f'Unsupported return type {type(res)}; response must be dict.')
                return {
                    'headers': res.get('headers', {}),
                    'statusCode': res.get('statusCode', 200),
                    'body': json.dumps(res['body'], iterable_as_array=True) if 'body' in res else None,
                }
            except HTTPResponseException as err:
                return {
                    'statusCode': 500,
                    'body': json.dumps(err.body, iterable_as_array=True),
                }
            except Exception as err:
                logger.exception(err)
                lambda_function_name = context.function_name.split('.')[-1].replace('_', ' ')
                return {
                    'statusCode': 500,
                    'body': default_error_message or f'Failed to {lambda_function_name}.',
                }

        return handler_wrapper
    return http_response_handler


def pausable(handler):
    """ Decorator that will "pause', i.e. short circuit and return immediately before calling
    the decorated handler, if the PAUSE environment variable is set.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a pausable lambda handler
    """
    @environ_aware([], ['PAUSE'])
    def handler_wrapper(event, context, **kwargs):
        if kwargs.get('PAUSE'):
            logger.warning('Function paused')
            return {'statusCode': 503, 'body': 'info: paused'}
        return handler(event, context, **kwargs)
    return handler_wrapper


def pingable(handler):
    """ Decorator that will short circuit and return immediately before calling
    the decorated handler if the event is a "ping" event.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a pingable lambda handler
    """
    def handler_wrapper(event, context, **kwargs):
        if event.get('detail-type') == 'Scheduled Event' and event.get('source') == 'aws.events':
            logger.debug('Ping received, keeping function alive')
            return 'info: ping'
        return handler(event, context, **kwargs)

    return handler_wrapper


def publisher(handler):
    """ Decorator that will publish messages to SNS Topics. This decorator looks for a 'messages'
    key in the result of the wrapper decorator. It expects result['messages'] to be a dict where
    key is Topic Name or ARN and value is the message to be sent. It will publish each message to
    its respective Topic.

    For example:

    response['messages'] = {
        'topic-1': 'string message',
        'topic-2': {'dictionary': 'message'},
    }

    Args:
        handler (func): lambda handler whose result will be checked for messages to publish

    Returns:
        handler (func): a publishing lambda handler
    """

    @account_id_aware
    @namespace_aware
    @region_aware
    def handler_wrapper(event, context, **kwargs):
        result = handler(event, context, **kwargs)
        conn = publish.conn(kwargs['region'], kwargs['account_id'], kwargs['NAMESPACE'])
        publish.publish(conn, result.get('messages', {}))
        return result

    return handler_wrapper


def subscriber(required_topics=None):
    """ Decorator that will grab messages from sns location in event body.

    Args:
        required_topics (iterable): Handler must be triggered by one of these Topics

    Returns:
        handler (func): a lambda handler function that is namespace aware
    """
    def subscriber_handler(handler):
        def handler_wrapper(event, context, **kwargs):
            try:
                sns = event['Records'][0]['Sns']
            except Exception:
                raise Exception('Unsupported event format.')
            if required_topics and not any((topic_name in sns['TopicArn'] for topic_name in required_topics)):
                raise Exception('Message received not from expected topic.')
            try:
                message_body = json.loads(sns.get('Message'))
            except Exception as err:
                raise Exception('Could not decode message.')

            kwargs['message'] = message_body

            return handler(event, context, **kwargs)

        return handler_wrapper

    return subscriber_handler


def configuration_aware(config_file, create=False):
    """ Decorator that expects a configuration file in an S3 Bucket specified by the 'CONFIG'
    environment variable and S3 Bucket Key (path) specified by config_file. If create=True, this
    decorator will create an empty configuration file instead of erring.

    Args:
        config_file (str): key in the 'CONFIG' S3 bucket of expected configuration file
        create (Bool): optionally create configuration file if absent

    Returns:
        handler (func): a configuration aware lambda handler
    """
    def configuration_handler(handler):
        config_bucket = os.environ['CONFIG']
        encrypt_key_arn = os.environ.get('ENCRYPT_KEY_ARN')

        conn = conf.conn(encrypt_key_arn)
        try:
            settings = conf.load_or_create(conn, config_bucket, config_file) if create else conf.load(
                conn, config_bucket, config_file)
        except Exception as err:
            logger.exception(err)
            logger.error('Failed to load or create configuration.')
            return {'statusCode': 503, 'body': 'Failed to load configuration.'}

        configuration = {
            'load': lambda: settings or {},
            'save': functools.partial(conf.save, conn, config_bucket, config_file),
        }

        def handler_wrapper(event, context, **kwargs):
            return handler(event, context, configuration=configuration, **kwargs)

        return handler_wrapper

    return configuration_handler


def client_config_aware(handler):
    """ Decorator that will find the Source IP and Client in the event headers.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a client config aware lambda handler
    """
    def handler_wrapper(event, context, **kwargs):
        client_details = tools.get_client_details(event)
        logger.info(f"{handler.__name__} | {client_details}")
        logger.debug(f'aws_lambda_wrapper| {event}')
        kwargs['client_details'] = client_details
        return handler(event, context, **kwargs)
    return handler_wrapper


def region_aware(handler):
    """ Decorator that will find the Account Region in the lambda context.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a region aware lambda handler
    """
    def handler_wrapper(event, context, **kwargs):
        region = tools.get_region(context)
        kwargs['region'] = region
        return handler(event, context, **kwargs)
    return handler_wrapper


def account_id_aware(handler):
    """ Decorator that will find the Account ID in the lambda context.

    Args:
        handler (func): a handler function with the signature (event, context) -> result

    Returns:
        handler (func): a context aware lambda handler
    """
    def handler_wrapper(event, context, **kwargs):
        account_id = tools.get_account_id(context)
        kwargs['account_id'] = account_id
        return handler(event, context, **kwargs)
    return handler_wrapper


def default(default_error_message=None):
    """
    AWS lambda handler handler. A wrapper with standard boilerplate implementing the
    best practices we've developed

    Returns:
        The wrapped lambda function or JSON response function when an error occurs.  When called,
        this wrapped function will return the appropriate output
    """

    def default_handler(handler):

        @http_response(default_error_message)
        @account_id_aware
        @client_config_aware
        @configuration_aware('configuration.json', True)
        @environ_aware(['NAMESPACE', 'CONFIG'], ['ENCRYPT_KEY_ARN'])
        @pingable
        def handler_wrapper(event, context, **kwargs):
            try:
                return handler(event, context, **kwargs)
            except Exception as err:
                logger.error('Lambda Event : {}'.format(event))
                logger.exception('{}:{}'.format(type(err), err))
                return {'statusCode': 500, 'body': f'Could not complete {handler.__name__}'}

        return handler_wrapper

    return default_handler
