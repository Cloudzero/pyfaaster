# pyfaaster
Useful Utilities for Python Functions as a Service (starting with AWS Lambda).

## Concept

Functions as a Service can be joyful. When paired with a concise language like Python, you start to
rethink the need for a "web framework" like Rails, Django, etc: couple your functions with your
FaaS provider's API Gateway and you are off an running with minimal code. 

Of course, there is still some boilerplate code around injecting environment, formatting responses,
checking arguments, etc. The goal of [pyfaaster](https://github.com/Cloudzero/pyfaaster) is to cut
through the cruft and get you humming along with your Python Functions ... as a service.

## Examples

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
    assert configuration == < contents of 'CONFIG' S3 bucket / config.json >
```


### Configuration Files

Similarly, don't worry about injecting those S3 Configuration files.

```
import pyfaaster as faas

@faas.configuration_aware('config.json', True)   # S3 key to a config file, create if not there
def handler(event, context, configuration=None):
    assert configuration == < contents of 'CONFIG' S3 bucket / config.json >
```
