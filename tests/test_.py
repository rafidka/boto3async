from boto3 import client
from boto3async import _camel_to_snake, asyncify_client


def test_camelcase_to_snakecase():
    assert _camel_to_snake('TestVariable') == 'test_variable'
    assert _camel_to_snake('Test123Variable') == 'test123_variable'
    assert _camel_to_snake('testVariable') == 'test_variable'
    assert _camel_to_snake('testHTTPMethod') == 'test_http_method'


def test_asyncify_client():
    s3_client = asyncify_client(client('s3'))

    for operation in s3_client._service_model.operation_names:
        operation_camelcase = _camel_to_snake(operation)
        assert getattr(s3_client, f'{operation_camelcase}_async') is not None
