"""
Utilities for dockorm tests.
"""
# encoding: utf-8
from __future__ import unicode_literals
from os.path import (
    dirname,
    join,
)

from six import iteritems

from ..container import (
    Container,
    scalar,
)


TEST_ORG = 'dockorm_testing'
TEST_TAG = 'test'


def assert_in_logs(container, line):
    """
    Assert that the given lines are in the container's logs.
    """
    logs = scalar(container.logs(all=True))
    validate_dict(logs, {'Logs': line})


def dockerfile_root(path):
    """
    Path to a directory Dockerfile for testing.
    """
    return join(
        dirname(__file__),
        'dockerfiles',
        path,
    )


def make_container(image, **kwargs):
    return Container(
        image=image,
        build_path=dockerfile_root(image),
        organization=TEST_ORG,
        tag=TEST_TAG,
        **kwargs
    )


def volume(path):
    """
    Path to a file relative to the test volumes directory.
    """
    return join(
        dirname(__file__),
        'volumes',
        path,
    )


def validate_dict(to_test, expected):
    """
    Recursively validate a dictionary of expectations against another input.

    Like TestCase.assertDictContainsSubset, but recursive.
    """
    for key, value in iteritems(expected):
        if isinstance(value, dict):
            validate_dict(to_test[key], value)
        else:
            assert to_test[key] == value
