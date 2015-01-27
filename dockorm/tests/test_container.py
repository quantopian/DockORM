# encoding: utf-8
from __future__ import unicode_literals

from docker.errors import APIError
from pytest import raises

from ..container import (
    scalar,
)
from .utils import (
    assert_in_logs,
    TEST_ORG,
    TEST_TAG,
    make_container,
    validate_dict,
    volume,
)


def checked_join(container):
    container.join()
    assert container.running() is None
    return container.inspect()


def checked_purge(container):
    container.purge()
    assert container.running() is None
    assert container.instances() == []


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
    checked_join(busybox)

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
        busybox.inspect()
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

    busybox.build()
    stdout, stderr = capsys.readouterr()
    assert stderr == ''
    stdout = stdout.splitlines()
    assert len(stdout) == 8
    assert stdout[0] == 'Step 0 : FROM busybox'
    assert stdout[1].startswith(' --->')
    assert stdout[2] == 'Step 1 : RUN echo testing'
    assert stdout[3].startswith(' ---> Running in')
    assert stdout[4] == 'testing'
    assert stdout[5].startswith(' --->')
    assert stdout[6].startswith('Removing intermediate container')
    assert stdout[7].startswith('Successfully built')

    image = scalar(busybox.images())
    assert image['RepoTags'] == [
        '{}/{}:{}'.format(TEST_ORG, 'busybox', TEST_TAG)
    ]

    busybox.remove_images()
    assert busybox.images() == []


def test_build_failed_pull(capsys):
    orphan = make_container('orphan')
    orphan.build()
    stdout, stderr = capsys.readouterr()
    assert stderr == ''
    stdout = stdout.splitlines()
    assert len(stdout) == 3
    assert(
        stdout[0] ==
        "Step 0 : FROM dockorm_fake_org/dockorm_fake_image:dockorm_fake_tag"
    )
    assert (
        stdout[1] ==
        'Pulling repository dockorm_fake_org/dockorm_fake_image'
    )
    assert (
        stdout[2] ==
        "Error: image dockorm_fake_org/dockorm_fake_image:dockorm_fake_tag "
        "not found"
    )
