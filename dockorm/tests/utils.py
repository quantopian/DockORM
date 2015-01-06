"""
Utilities for dockorm tests.
"""
# encoding: utf-8
from __future__ import unicode_literals
from os.path import (
    dirname,
    join,
)

from ..container import Container

TEST_ORG = 'dockorm_testing'
TEST_TAG = 'test'


def dockerfile_root(path):
    """
    Path to a directory Dockerfile for testing.
    """
    return join(
        dirname(__file__),
        'dockerfiles',
        path,
    )


def test_container(image, **kwargs):
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
