from boto3async.dummy import dummy


def test_dummy():
    assert dummy() == True
