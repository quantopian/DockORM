# encoding: utf-8
"""
Container class.
"""
from __future__ import print_function, unicode_literals
from itertools import chain
import json
from subprocess import call

from docker import Client
from docker.utils import (
    create_host_config,
    kwargs_from_env,
)
from six import (
    iteritems,
    itervalues,
    string_types,
    text_type,
)


from traitlets import (
    Any,
    Dict,
    HasTraits,
    Instance,
    List,
    Unicode,
    TraitError,
)

from .py3compat_utils import strict_map


def print_build_output(build_output):
    success = True
    for raw_message in build_output:
        message = json.loads(raw_message.decode('ascii'))
        if 'stream' in message:
            print(message['stream'], end="")
        elif 'status' in message:
            print(message['status'])
        elif 'error' in message:
            success = False
            print(message['error'])
        else:
            success = False
            print("Unknown message during build: %s" % message)
    return success


def scalar(l):
    """
    Get the first and only item from a list.
    """
    assert len(l) == 1
    return l[0]


class Container(HasTraits):
    """
    A specification for creation of a container.
    """

    organization = Unicode()

    def _organization_changed(self, name, old, new):
        if new and not new.endswith('/'):
            self.organization = new + '/'

    image = Unicode()

    def _image_changed(self, name, old, new):
        if not new:
            raise TraitError("Must supply a value for image.")

    tag = Unicode(default_value='latest')

    def full_imagename(self, tag=None):
        return '{}{}:{}'.format(
            self.organization,
            self.image,
            tag or self.tag,
        )

    name = Unicode()

    def _name_default(self):
        return self.image + '-running'

    build_path = Unicode()

    links = List(Instance(__name__ + '.Link'))

    def format_links(self):
        return {}

    volumes_readwrite = Dict()

    volumes_readonly = Dict()

    @property
    def volume_mount_points(self):
        """
        Volumes are declared in docker-py in two stages.  First, you declare
        all the locations where you're going to mount volumes when you call
        create_container.

        Returns a list of all the values in self.volumes or
        self.read_only_volumes.
        """
        return list(
            chain(
                itervalues(self.volumes_readwrite),
                itervalues(self.volumes_readonly),
            )
        )

    @property
    def volume_binds(self):
        """
        The second half of declaring a volume with docker-py happens when you
        actually call start().  The required format is a dict of dicts that
        looks like:

        {
            host_location: {'bind': container_location, 'ro': True}
        }
        """
        volumes = {
            key: {'bind': value, 'ro': False}
            for key, value in iteritems(self.volumes_readwrite)
        }
        ro_volumes = {
            key: {'bind': value, 'ro': True}
            for key, value in iteritems(self.volumes_readonly)
        }
        volumes.update(ro_volumes)
        return volumes

    ports = Dict(
        help="Map from container port -> host port. "
        "See http://docker-py.readthedocs.org/en/latest/port-bindings/."
    )

    @property
    def port_bindings(self):
        out = {}
        for key, value in iteritems(self.ports):
            if isinstance(key, tuple):
                # Convert (1111, 'udp') -> '1111/udp'
                key = '/'.join(strict_map(text_type, key))
            out[key] = value
        return out

    @property
    def open_container_ports(self):
        out = []
        for key in self.ports:
            if isinstance(key, int):
                to_append = key
            elif isinstance(key, string_types):
                to_append = int(key)
            elif isinstance(key, tuple):
                to_append = key[0]
            else:
                raise TypeError("Couldn't understand port key %s" % key)
            out.append(to_append)
        return out

    environment = Dict()

    network_mode = Unicode(
        default_value="bridge",
        help="network_mode for start",
    )

    extra_hosts = Dict(
        help="Extra entries for container /etc/hosts",
    )

    def _make_host_config(self):
        return create_host_config(
            binds=self.volume_binds,
            port_bindings=self.port_bindings,
            network_mode=self.network_mode,
            extra_hosts=self.extra_hosts,
            # TODO: Support all of these.
            lxc_conf=None,
            publish_all_ports=False,
            links=None,
            privileged=False,
            dns=None,
            dns_search=None,
            volumes_from=None,
            restart_policy=None,
            cap_add=None,
            cap_drop=None,
            devices=None,
            read_only=None,
            pid_mode=None,
            ipc_mode=None,
            security_opt=None,
            ulimits=None,
            log_config=None,
        )

    # This should really be something like:
    # Either(Instance(str), List(Instance(str)))
    command = Any()

    client = Instance(Client, kw=kwargs_from_env(), allow_none=True)

    def build(self, tag=None, display=True, rm=True):
        """
        Build the container.

        If display is True, write build output to stdout.  Otherwise return it
        as a generator.
        """
        output = self.client.build(
            self.build_path,
            self.full_imagename(tag=tag),
            # This is in line with the docker CLI, but different from
            # docker-py's default.
            rm=rm,
        )
        if display:
            return print_build_output(output)
        else:
            return list(output)

    def run(self, command=None, tag=None, attach=False, rm=False):
        """
        Run this container.
        """
        if rm and not attach:
            raise ValueError(
                "Auto-remove is not supported with detached execution."
            )

        container = self.client.create_container(
            self.full_imagename(tag),
            name=self.name,
            ports=self.open_container_ports,
            volumes=self.volume_mount_points,
            detach=not attach,
            stdin_open=attach,
            tty=attach,
            command=command or self.command,
            environment=self.environment,
            host_config=self._make_host_config(),
        )

        self.client.start(container)

        if attach:
            call(['docker', 'attach', self.name])
            if rm:
                self.client.remove_container(self.name)

    def _matches(self, container):
        return '/' + self.name in container['Names']

    def instances(self, all=True):
        """
        Return any instances of this container, running or not.
        """
        return [
            c for c in self.client.containers(all=all) if self._matches(c)
        ]

    def running(self):
        """
        Return the running instance of this container, or None if no container
        is running.
        """
        container = self.instances(all=False)
        if container:
            return scalar(container)
        else:
            return None

    def stop(self):
        self.client.stop(self.name)

    def purge(self, stop_first=True, remove_volumes=False):
        """
        Purge all containers of this type.
        """
        for container in self.instances():
            if stop_first:
                self.client.stop(container)
            else:
                self.client.kill(container)
            self.client.remove_container(
                container,
                v=remove_volumes,
            )

    def inspect(self, tag=None):
        """
        Inspect any running instance of this container.
        """
        return self.client.inspect_container(
            self.name,
        )

    def images(self):
        """
        Return any images matching our current organization/name.

        Does not filter by tag.
        """
        return self.client.images(self.full_imagename().split(':')[0])

    def remove_images(self):
        """
        Remove any images matching our current organization/name.

        Does not filter by tag.
        """
        for image in self.images():
            self.client.remove_image(image)

    def logs(self, all=False):
        return [
            {
                'Id': container,
                'Logs': self.client.logs(container)
            }
            for container in self.instances(all=all)
        ]

    def join(self):
        """
        Wait until there are no instances of this container running.
        """
        container = self.running()
        if container:
            self.client.wait(container)


class Link(HasTraits):
    """
    A link between containers.
    """
    container = Instance(Container)
    alias = Unicode()
