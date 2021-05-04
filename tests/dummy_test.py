from boto3_async.dummy import dummy


def test_dummy():
    assert dummy() == True
