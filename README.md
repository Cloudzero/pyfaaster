# pyfaaster

[![Build Status](https://semaphoreci.com/api/v1/projects/0234f02a-6a7c-443d-ac66-7c2a17c1922a/1756352/badge.svg)](https://semaphoreci.com/cloudzero/pyfaaster)

Useful Utilities for Python Functions as a Service (starting with AWS Lambda).

## Problem

Functions as a Service can be joyful. When paired with a concise language like Python, you start to
rethink the need for a "web framework" like Rails, Django, etc: couple your functions with your
FaaS provider's API Gateway and you are off an running with minimal code. Of course, there is still some boilerplate code around injecting environment, formatting responses, checking arguments, etc. 

## Concept

The goal of [pyfaaster](https://github.com/Cloudzero/pyfaaster) is to cut
through the cruft and get you humming along with your Python FaaS. `pyfaaster` accomplishes
this goal by providing you with useful middleware (i.e. decorators) for your lambda functions. Additionally, `pyfaaster` can be used for its excellent `Makefile` and `serverless.yml` examples.

Cheers!


## Usage

The following is a non-exhaustive list and details of the useful middleware. More can be found in `pyfaaster.aws.handler_decorators`.

### Environment Variables

You don't want to sprinkle `os.environ` throughout your code. Let us do that for you.

```
import pyfaaster as faas

@faas.environ_aware(['REQUIRED_ENV'], ['OPTIONAL_ENV'])
def handler(event, context, REQUIRED_ENV=None, OPTIONAL_ENV=None):
    assert REQUIRED_ENV == os.environ['REQUIRED_ENV']     # <- faas.environ_aware will return early with a useful message if this is not set
    assert OPTIONAL_ENV == os.environ.get('OPTIONAL_ENV')
```


### Configuration Files

Similarly, don't worry about injecting those S3 Configuration files.

```
import pyfaaster as faas

@faas.configuration_aware('config.json', True)   # S3 key to a config file, create if not there
def handler(event, context, configuration=None):
    assert configuration == < { 
    'load': lambda : {contents of config bucket},
    'save': lambda d : save d into config bucket,
    }
```


### Response Format

Sigh, you have to manually convert your lambda return values to API Gateway's expected dictionary? Don't forget to serialize all your json into the `body` element! Oh wait ... just use


```
import pyfaaster as faas

@faas.http_response(default_error_message='Failed to handle something.")
def handler(event, context, **kwargs):
    return { 'my': 'important', 'json': 'data'} # <- will end up as the json serialized `body` in an API Gateway compatible dict with statusCode.
```


### Authorization

You gotta confirm your token scopes, friend!


```
import pyfaaster as faas

# Checks the event.requestContext.authorizer for the given scopes. This works nicely with AWS custom
# authorizers. An example one is coming to this library soon.

@faas.scopes('read:profile', 'update:email')
def handler(event, context, **kwargs):
    return 'Hello, Secure World!'
```
