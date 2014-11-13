# encoding: utf-8
from __future__ import unicode_literals

from docker.errors import APIError
from pytest import raises
from six import iteritems

from .conftest import (
    TEST_ORG,
    TEST_TAG,
)
from ..container import scalar, Container


def checked_join(container):
    container.join()
    assert container.running() is None
    return container.inspect()


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


def test_container_run(busybox):
    busybox.run(['false'])
    instance = scalar(busybox.instances())

    validate_dict(
        instance,
        {
            'Command': 'false',
            'Names': ['/busybox-running'],
            'Image': '{}/{}:{}'.format(TEST_ORG, 'busybox', TEST_TAG)
        }
    )

    details = checked_join(busybox)

    validate_dict(
        details,
        {
            'State': {
                'ExitCode': 1,
                'Running': False,
            }
        }
    )


def test_container_join(busybox):

    busybox.run(['sleep', '1'])

    instance = busybox.running()
    assert instance is not None
    assert instance['Command'] == 'sleep 1'

    details = busybox.inspect()
    validate_dict(
        details,
        {
            'State': {
                'ExitCode': 0,
                'Running': True,
            }
        }
    )

    details = checked_join(busybox)

    validate_dict(
        details,
        {
            'State': {
                'ExitCode': 0,
                'Running': False,
            }
        }
    )


def test_container_logs(busybox):
    busybox.run(['echo', 'foo'])
    checked_join(busybox)

    logs = scalar(busybox.logs(all=True))
    validate_dict(logs, {'Logs': b'foo\n'})


def test_container_purge(busybox):
    busybox.run(['true'])
    details = checked_join(busybox)
    assert details

    busybox.purge()

    assert busybox.running() is None
    assert busybox.instances() == []
    with raises(APIError) as e:
        val = busybox.inspect()
    assert e.value.response.status_code == 404


def test_container_build_remove(busybox, capsys):
    # Ensure that we actually do a build.
    busybox.remove_images()

    output = busybox.build()
    stdout, stderr = capsys.readouterr()

    # NOTE: docker-py drops the first line of normal build output.
    assert stderr == ''
    stdout = stdout.splitlines()
    assert stdout[1] == 'Step 1 : RUN echo testing'
    assert stdout[3] == 'testing'
    assert stdout[5].startswith('Successfully built')

    image = scalar(busybox.images())
    assert image['RepoTags'] == [
        '{}/{}:{}'.format(TEST_ORG, 'busybox', TEST_TAG)
    ]

    busybox.remove_images()
    assert busybox.images() == []
