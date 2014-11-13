# encoding: utf-8
from __future__ import unicode_literals

from docker import Client
from pytest import fixture

from ..container import Container
from .utils import dockerfile_root

TEST_ORG = 'dockorm_testing'
TEST_TAG = 'test'


def test_container(image, **kwargs):
    return Container(
        image=image,
        build_path=dockerfile_root(image),
        organization=TEST_ORG,
        tag=TEST_TAG,
        **kwargs
    )


@fixture(scope='session', autouse=True)
def clean_test_images():
    """
    Automatically clear all test images at the end of a test run.
    """
    client = Client()
    test_images = client.images(TEST_ORG + "/*")
    for image in test_images:
        client.remove_image(image)


@fixture
def busybox(request):
    client = Client()
    bb = test_container('busybox')

    if not bb.images():
        bb.build(display=False)

    def clean():
        bb.purge(stop_first=False, remove_volumes=True)

    request.addfinalizer(clean)

    return bb
