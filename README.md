# boto3async

Extension to boto3 supporting async functions.

# Overview

[boto3](https://github.com/boto/boto3) Python library is used for interacting with AWS services in
Python. One big disadvantage of it is the lack of [asyncio](https://docs.python.org/3/library/asyncio.html)
support, which is becoming increasingly popular in multiple programming languages, Python included.
`boto3async` library is what you need for that.

# Features

- **Support all AWS client APIs**: To avoid having to manually add async wrapper methods, which results
  in a lag between when a method is supported in boto3 and when boto3async supports it, the creation of
  of the async version of the methods are automated based on the existing methods of a certain boto3 client.
- **Follow a simple naming convention**: To every method of a boto3 client, a method having the same name
  but postfixed with `_async` is created. Thus, existing boto3 code can be asyncified by simply 1)
  creating a boto3async client instead of a boto3 client and 2) changing existing calls to the
  clients by adding `await` before the call and postfixing the name with `_async`.
- **Apache-2.0 licensed**: To free the current users of boto3 from having to worry about licensing, this
  library adopted the same license that [boto3 uses](https://github.com/boto/boto3/blob/d68969f/LICENSE).

# Installation

This package is available in PyPI, so it can be installed via `pip`. At the moment, however, I have only
pushed the package to the test PyPI index, so you have to install it like the following:

```
pip install -i https://test.pypi.org/simple/ -U boto3async
```

This is just temporary while the package is polished a little bit more, and then I will publish it to PyPI.

# Example

Assume we have the following code that lists the S3 buckets in a certain account:

```python
import boto3

def main():
    s3 = boto3.client('s3')
    response = s3.list_buckets()
    print(response)

main()
```

The equivalent async code would be the following:

```python
import asyncio

import boto3async

async def main():
    s3 = boto3async.client('s3')
    response = await s3.list_buckets_async()
    print(response)


asyncio.run(main())
```

In short, these are the three required steps:

- Use `boto3async.client` instead of `boto3.client`.
- Append `_async` to the method name.
- Prefix the call with `await`.

# How does it work?

The underlying idea is simple: for every method covering a certain operation, e.g. `list_buckets`,
create a counterpart async method, `list_buckets_async` in this case, that execute the sync method
in a Python thread via Python's [to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
function.

For example, let's manually create an async version of the `list_buckets` method.

```python
import asyncio

async def list_bucktes_async():
    s3_client = boto3.client('s3')
    return await asyncio.to_thread(s3_client.list_buckets)
```

Now, having this async function, we can use it like this:

```python
async def main():
    response = await list_bucktes_async()
    print(json.dumps(response, default=str, indent=2))

asyncio.run(main())
```

Now, all we need is to automate the creation of those methods, which is not difficult
with a function like this:

```python
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
```

This function is automatically called when the user calls `boto3async.client` function,
thus returning to the user a normal boto3 client, but with async version of every
operation.

# But what about the Global Interpreter Lock?

CPython is the default and most widely used implementation of the Python programming language. In
CPython, executing the same bytecode by more than one thread is blocked by the [Global Interpreter
Lock](https://wiki.python.org/moin/GlobalInterpreterLock). Since the mechanism of this library
depends on creating another thread (via `to_thread` method) that execuse the sync version of the
method, e.g. `list_buckets`, doesn't that mean if we have more than one call to, say, `list_buckets_async`,
one of them will block the other?

Fortunately, this is not the case. In fact, the [primary intention of `to_thread`](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
is to "to be used for executing IO-bound functions/methods that would otherwise block the event loop
if they were ran in the main thread.

Let's try the following code to confirm we are indeed able to make multiple request at the same
time:

```python
import asyncio
from datetime import datetime

import boto3async

s3 = boto3async.client('s3')

# Do a request to warm-up the client.
s3.list_buckets()

async def call_list_buckets_async(call_id):
    print(f"[{call_id}] Execution started at {datetime.now()}")
    response = await s3.list_buckets_async()
    print(f"[{call_id}] Execution ended at {datetime.now()}")
    return response

async def main():
    await asyncio.gather(*map(
        lambda id: call_list_buckets_async(f"test{id}"),
        range(20))
    )

asyncio.run(main())
```

As you can see, I am trying to make multiple calls to retrieve buckets. Let's
see the output:

```
[test0] Execution started at 2021-05-07 18:30:30.411705
[test1] Execution started at 2021-05-07 18:30:30.412699
[test2] Execution started at 2021-05-07 18:30:30.413613
[test3] Execution started at 2021-05-07 18:30:30.414507
[test4] Execution started at 2021-05-07 18:30:30.415411
[test5] Execution started at 2021-05-07 18:30:30.416224
[test6] Execution started at 2021-05-07 18:30:30.417046
[test7] Execution started at 2021-05-07 18:30:30.417996
[test8] Execution started at 2021-05-07 18:30:30.418864
[test9] Execution started at 2021-05-07 18:30:30.419723
[test10] Execution started at 2021-05-07 18:30:30.420627
[test11] Execution started at 2021-05-07 18:30:30.421442
[test12] Execution started at 2021-05-07 18:30:30.422245
[test13] Execution started at 2021-05-07 18:30:30.423033
[test14] Execution started at 2021-05-07 18:30:30.423750
[test15] Execution started at 2021-05-07 18:30:30.424513
[test16] Execution started at 2021-05-07 18:30:30.425301
[test17] Execution started at 2021-05-07 18:30:30.425375
[test18] Execution started at 2021-05-07 18:30:30.425406
[test19] Execution started at 2021-05-07 18:30:30.425434
[test0] Execution ended at 2021-05-07 18:30:30.505919
[test16] Execution ended at 2021-05-07 18:30:30.598505
[test17] Execution ended at 2021-05-07 18:30:30.698157
[test1] Execution ended at 2021-05-07 18:30:30.786313
[test6] Execution ended at 2021-05-07 18:30:30.786337
[test2] Execution ended at 2021-05-07 18:30:30.786347
[test4] Execution ended at 2021-05-07 18:30:30.786356
[test5] Execution ended at 2021-05-07 18:30:30.795578
[test18] Execution ended at 2021-05-07 18:30:30.795624
[test15] Execution ended at 2021-05-07 18:30:30.798291
[test8] Execution ended at 2021-05-07 18:30:30.799903
[test14] Execution ended at 2021-05-07 18:30:30.806013
[test13] Execution ended at 2021-05-07 18:30:30.806049
[test9] Execution ended at 2021-05-07 18:30:30.808229
[test10] Execution ended at 2021-05-07 18:30:30.811141
[test11] Execution ended at 2021-05-07 18:30:30.812765
[test3] Execution ended at 2021-05-07 18:30:30.814323
[test12] Execution ended at 2021-05-07 18:30:30.816715
[test19] Execution ended at 2021-05-07 18:30:30.881881
[test7] Execution ended at 2021-05-07 18:30:31.030565

```

As we can see the execution of those 20 requests took about 619 ms in total.
In comparison, let's execute those requests in serial (without the use of `gather`):

```python
import asyncio
from datetime import datetime

import boto3async

s3 = boto3async.client('s3')

# Do a request to warm-up the client.
s3.list_buckets()

async def call_list_buckets_async(call_id):
    print(f"[{call_id}] Execution started at {datetime.now()}")
    response = await s3.list_buckets_async()
    print(f"[{call_id}] Execution ended at {datetime.now()}")
    return response

async def main():
    # await asyncio.gather(*map(
    #     lambda id: call_list_buckets_async(f"test{id}"),
    #     range(20))
    # )
    for id in range(20):
        await call_list_buckets_async(f"test{id}")

asyncio.run(main())
```

Running the above, I got the following output:

```
[test0] Execution started at 2021-05-07 18:32:19.555753
[test0] Execution ended at 2021-05-07 18:32:19.657219
[test1] Execution started at 2021-05-07 18:32:19.657238
[test1] Execution ended at 2021-05-07 18:32:19.760870
[test2] Execution started at 2021-05-07 18:32:19.760948
[test2] Execution ended at 2021-05-07 18:32:19.864968
[test3] Execution started at 2021-05-07 18:32:19.865060
[test3] Execution ended at 2021-05-07 18:32:19.961329
[test4] Execution started at 2021-05-07 18:32:19.961347
[test4] Execution ended at 2021-05-07 18:32:20.056802
[test5] Execution started at 2021-05-07 18:32:20.056836
[test5] Execution ended at 2021-05-07 18:32:20.153065
[test6] Execution started at 2021-05-07 18:32:20.153084
[test6] Execution ended at 2021-05-07 18:32:20.246739
[test7] Execution started at 2021-05-07 18:32:20.246758
[test7] Execution ended at 2021-05-07 18:32:20.407346
[test8] Execution started at 2021-05-07 18:32:20.407374
[test8] Execution ended at 2021-05-07 18:32:20.501308
[test9] Execution started at 2021-05-07 18:32:20.501327
[test9] Execution ended at 2021-05-07 18:32:20.595743
[test10] Execution started at 2021-05-07 18:32:20.595766
[test10] Execution ended at 2021-05-07 18:32:20.688998
[test11] Execution started at 2021-05-07 18:32:20.689018
[test11] Execution ended at 2021-05-07 18:32:20.783286
[test12] Execution started at 2021-05-07 18:32:20.783318
[test12] Execution ended at 2021-05-07 18:32:20.887521
[test13] Execution started at 2021-05-07 18:32:20.887600
[test13] Execution ended at 2021-05-07 18:32:20.989157
[test14] Execution started at 2021-05-07 18:32:20.989233
[test14] Execution ended at 2021-05-07 18:32:21.109131
[test15] Execution started at 2021-05-07 18:32:21.109150
[test15] Execution ended at 2021-05-07 18:32:21.205840
[test16] Execution started at 2021-05-07 18:32:21.205863
[test16] Execution ended at 2021-05-07 18:32:21.303624
[test17] Execution started at 2021-05-07 18:32:21.303684
[test17] Execution ended at 2021-05-07 18:32:21.407096
[test18] Execution started at 2021-05-07 18:32:21.407188
[test18] Execution ended at 2021-05-07 18:32:21.507647
[test19] Execution started at 2021-05-07 18:32:21.507665
[test19] Execution ended at 2021-05-07 18:32:21.633140
```

Now it took 2077 ms in total, vs 619 ms from the parallel execution.

# Caveats

- ~~This library depends on Python's [to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
  function. Unfortunately, this function is only supported in Python 3.9 and beyond, hence this library
  only runs on Python 3.9 and beyond.~~ I copied the implementation of `to_thread` from Python 3.9's
  [source code](https://github.com/python/cpython/blob/a0bd9e9c11/Lib/asyncio/threads.py#L12-L25) so
  now the library works on Python 3.7 and later.
- Only [clients](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/clients.html), i.e.
  what are created via `boto3.client('xyz')`, support async methods; there is no support for resources
  at the moment. The reason is that [resources](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html)
  are higher level constructs and it is not easy to automate the generation of async counterparts
  of the existing sync methods.
