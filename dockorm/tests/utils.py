"""
Utilities for dockorm tests.
"""

# encoding: utf-8
from __future__ import unicode_literals
from os.path import (
    dirname,
    join,
)


def dockerfile_root(path):
    """
    Path to a directory Dockerfile for testing.
    """
    return join(
        dirname(__file__),
        'dockerfiles',
        path,
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
