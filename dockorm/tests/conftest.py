# encoding: utf-8
from __future__ import unicode_literals

from docker import Client
from docker.utils import kwargs_from_env
from pytest import fixture

from .utils import (
    TEST_ORG,
    make_container,
)


@fixture(scope='session', autouse=True)
def clean_test_images(request):
    """
    Automatically clear all test images after each test run.
    """
    def cleanup():
        client = Client(version='auto', **kwargs_from_env())
        test_images = client.images(TEST_ORG + "/*")
        for image in test_images:
            client.remove_image(image)
    cleanup()
    request.addfinalizer(cleanup)


@fixture
def busybox(request):
    bb = make_container('busybox')

    if not bb.images():
        bb.build(display=False)

    def clean():
        bb.purge(stop_first=False, remove_volumes=True)

    request.addfinalizer(clean)

    return bb


@fixture
def orphan(request):
    container = make_container('orphan')

    def clean():
        container.purge(stop_first=False, remove_volumes=True)

    request.addfinalizer(clean)

    return container


@fixture(scope='session', autouse=True)
def decoy(request):
    """
    An extra copy of the busybox container to run during all tests.

    Ensures that by-name filters correctly ignore differently-named containers.
    """
    bb = make_container('busybox_decoy')
    if not bb.images():
        bb.build(display=False)

    def clean():
        bb.purge(stop_first=False, remove_volumes=True)

    request.addfinalizer(clean)

    bb.run(['sleep', '2147483647'])
    assert bb.running()
