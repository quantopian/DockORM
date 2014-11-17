# encoding: utf-8
from __future__ import unicode_literals

from docker.errors import APIError
from pytest import raises
from six import iteritems

from .conftest import (
    TEST_ORG,
    TEST_TAG,
)
from .utils import volume
from ..container import scalar, Container


def checked_join(container):
    container.join()
    assert container.running() is None
    return container.inspect()


def checked_purge(container):
    container.purge()
    assert container.running() is None
    assert container.instances() == []


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


def assert_in_logs(container, line):
    """
    Assert that the given lines are in the container's logs.
    """
    logs = scalar(container.logs(all=True))
    validate_dict(logs, {'Logs': line})


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
    assert_in_logs(busybox, b'foo\n')


def test_container_environment(busybox):
    busybox.environment = {'FOO': 'foo'}
    busybox.run(
        ['env']
    )
    results = checked_join(busybox)

    env_dict = {
        pair[0]: pair[1] for pair in
        (
            message.split(b'=') for message in
            scalar(busybox.logs(all=True))['Logs'].splitlines()
        )
    }

    validate_dict(env_dict, {b'FOO': b'foo'})


def test_container_purge(busybox):
    busybox.run(['true'])
    details = checked_join(busybox)
    assert details

    checked_purge(busybox)

    with raises(APIError) as e:
        val = busybox.inspect()
    assert e.value.response.status_code == 404


def test_container_volumes_rw(busybox):
    volume_loc = volume('foo.txt')
    busybox.volumes_readwrite = {volume_loc: 'bar.txt'}
    busybox.run(['cat', 'bar.txt'])
    details = checked_join(busybox)
    validate_dict(
        details,
        {
            'Volumes': {'bar.txt': volume_loc},
            'VolumesRW': {'bar.txt': True}
        }
    )
    assert_in_logs(busybox, b'This is a volume!\n')


def test_container_volumes_ro(busybox):
    volume_loc = volume('foo.txt')
    busybox.volumes_readonly = {volume_loc: 'bar.txt'}
    busybox.run(['cat', 'bar.txt'])
    details = checked_join(busybox)
    validate_dict(
        details,
        {
            'Volumes': {'bar.txt': volume_loc},
            'VolumesRW': {'bar.txt': False}
        }
    )
    assert_in_logs(busybox, b'This is a volume!\n')


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
    assert stdout[-1].startswith('Successfully built')

    image = scalar(busybox.images())
    assert image['RepoTags'] == [
        '{}/{}:{}'.format(TEST_ORG, 'busybox', TEST_TAG)
    ]

    busybox.remove_images()
    assert busybox.images() == []
