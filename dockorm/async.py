# encoding: utf-8
from __future__ import unicode_literals
try:
    # Python3
    from concurrent.futures import ThreadPoolExecutor
except ImportError:
    from futures.thread import ThreadPoolExecutor

from docker import Client
from requests_futures.sessions import FuturesSession


class AsyncDockerClient(object):
    """
    Async wrapper around docker.Client that returns futures on all methods by
    running them on a thread pool.
    """
    def __init__(self, executor=None, **client_kwargs):
        if executor is None:
            executor = ThreadPoolExecutor(max_workers=1)
        self._executor = executor
        self._client = Client(**client_kwargs)

    def __getattr__(self, name):
        '''Creates a function, based on docker_client.name that returns a
        Future. If name is not a callable, returns the attribute directly.
        '''
        fn = getattr(self._client, name)

        # Make sure it really is a function first
        if not callable(fn):
            return fn

        def method(*args, **kwargs):
            return self._executor.submit(fn, *args, **kwargs)

        return method
