#!/bin/sh

[[ $(python --version) =~ 'Python 3' ]] || {
    echo "boto3_async requires Python 3."
}

pytest -v
