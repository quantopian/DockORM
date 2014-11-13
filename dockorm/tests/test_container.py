# encoding: utf-8
from __future__ import unicode_literals

from docker.errors import APIError
from pytest import raises
from six import iteritems

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
            'Names': ['/busybox-dockorm-testing'],
            'Image': 'busybox:latest',
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
    validate_dict(logs, {'Logs': 'foo\n'})


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
