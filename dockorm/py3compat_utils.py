"""
Utilities for python 2/3 compat.
"""
from __future__ import unicode_literals


def strict_map(func, iterable):
    """
    Python 2/3-agnostic strict map.
    """
    return [func(i) for i in iterable]
