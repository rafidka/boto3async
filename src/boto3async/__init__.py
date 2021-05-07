import asyncio
import boto3
import re

__version__ = '0.0.2'


# From https://stackoverflow.com/a/1176023/196697
def _camel_to_snake(name):
    """
    Convert a name in camel case to snake case.

    Arguments:
    name -- The name to convert.

    Returns:
    The name in snake case.
    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def asyncify_client(client):
    """
    Adds async methods to each of the sync methods of a boto3 client.

    Keyword arguments
    client -- The client to add sync methods to. Notice that the client
        will be updated in place, and will also be returned as a return
        value.

    Returns:
    The same client.
    """

    def create_async_func(sync_func):
        async def async_func(*args, **kwargs):
            return await asyncio.to_thread(sync_func, *args, **kwargs)
        return async_func

    for operation in client._service_model.operation_names:
        operation_camelcase = _camel_to_snake(operation)
        sync_func = getattr(client, operation_camelcase)
        async_func = create_async_func(sync_func)
        setattr(client, f'{operation_camelcase}_async', async_func)

    return client


def client(*args, **kwargs):
    """
    Create a normal boto3 client and add async methods to it.

    Arguments:
    See boto3 documentation for what arguments you need to pass to create the
    different AWS client.

    Returns:
    A boto3 client with async versions of each method. Each async method has
    the same name as the sync method, but with "_async" postfix. For example,
    the async version of list_buckets is named list_buckets_async.
    """
    client = boto3.client(*args, **kwargs)

    return asyncify_client(client)


def resource(*args, **kwargs):
    return boto3.resource(*args, **kwargs)
