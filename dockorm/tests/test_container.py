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


def test_container_extra_hosts(busybox):

    busybox.extra_hosts = {'www.test.com': '8.8.8.8'}

    busybox.run(['cat', '/etc/hosts'])
    assert(checked_join(busybox))

    logs_list = busybox.logs(all=True)
    assert len(logs_list) == 1

    actual_logs = logs_list[0]['Logs'].split(b'\n')
    assert b'8.8.8.8\twww.test.com' in actual_logs


def test_container_ports(busybox):
    busybox.ports = {
        1111: 1112,
        2222: None,
        (3333, 'udp'): 3334,
        4444: ('127.0.0.1', 4445),
    }

    busybox.run(['sleep', '2147483647'])

    instance = scalar(busybox.instances(all=True))
    expected_ports = [
        {
            'IP': '0.0.0.0',
            'PrivatePort': 1111,
            'PublicPort': 1112,
            'Type': 'tcp',
        },
        {
            'IP': '0.0.0.0',
            'PrivatePort': 2222,
            'Type': 'tcp',
            'PublicPort': 'UNKNOWN',  # Gets filled in below.
        },
        {
            'IP': '',
            'PrivatePort': 3333,
            'PublicPort': 3334,
            'Type': 'udp',
        },
        {'PrivatePort': 3333, 'Type': 'tcp'},
        {
            'IP': '127.0.0.1',
            'PrivatePort': 4444,
            'PublicPort': 4445,
            'Type': 'tcp'
        },
    ]
    received_ports = sorted(
        [
            data for data in instance['Ports']
        ],
        key=lambda d: (d['PrivatePort'], d.get('PublicPort', float('inf'))),
    )
    for i, data in enumerate(received_ports):
        if data['PrivatePort'] == 2222:
            expected_ports[i]['PublicPort'] = data['PublicPort']
            host_port_2222 = data['PublicPort']
        assert data == expected_ports[i]

    details = busybox.inspect()
    expected_host_config_ports = {
        '1111/tcp': [{'HostIp': '', 'HostPort': '1112'}],
        '2222/tcp': [{'HostIp': '', 'HostPort': ''}],
        '3333/udp': [{'HostIp': '', 'HostPort': '3334'}],
        '4444/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '4445'}],
    }
    assert details['HostConfig']['PortBindings'] == expected_host_config_ports

    expected_network_ports = {
        '1111/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '1112'}],
        '2222/tcp': [{'HostIp': '0.0.0.0', 'HostPort': str(host_port_2222)}],
        '3333/tcp': None,
        '3333/udp': [{'HostIp': '', 'HostPort': '3334'}],
        '4444/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '4445'}],
    }
    assert details['NetworkSettings']['Ports'] == expected_network_ports


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
