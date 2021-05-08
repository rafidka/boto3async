import asyncio
import boto3
import re
import functools
import contextvars

__version__ = '0.0.5'


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
            return await _to_thread(sync_func, *args, **kwargs)
        return async_func

    for operation in client._service_model.operation_names:
        operation_camelcase = _camel_to_snake(operation)
        sync_func = getattr(client, operation_camelcase)
        async_func = create_async_func(sync_func)
        setattr(client, f'{operation_camelcase}_async', async_func)

    return client


# The content of this function is copied from Python 3.9 source code as a
# backport to support earlier versions of Python:
#
# https://github.com/python/cpython/blob/a0bd9e9c11/Lib/asyncio/threads.py#L12-L25
#
# The function depends on the following other functions:
#
# - asyncio.events.get_running_loop (supported since Python 3.7):
#   https://docs.python.org/3.7/library/asyncio-eventloop.html#asyncio.get_running_loop
# - contextvars.copy_context (supported since at least Python 3.7):
#   https://docs.python.org/3.7/library/contextvars.html#contextvars.copy_context
# - BaseEventLoop.run_in_executor (supported since at least Python 3.4):
#   https://docs.python.org/3.4/library/asyncio-eventloop.html#asyncio.BaseEventLoop.run_in_executor
#
# So, based on the above, we need at least Python 3.7. Later on, we could dig deeper
# into the implementation of get_running_loop() to see if we can have a backport
# implementation for them as well to support earlier versions of Python.
async def _to_thread(func, *args, **kwargs):
    """Asynchronously run function *func* in a separate thread.

    Any *args and **kwargs supplied for this function are directly passed
    to *func*. Also, the current :class:`contextvars.Context` is propogated,
    allowing context variables from the main thread to be accessed in the
    separate thread.

    Return a coroutine that can be awaited to get the eventual result of *func*.
    """
    loop = asyncio.events.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


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
