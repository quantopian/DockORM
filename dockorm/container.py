# encoding: utf-8
"""
Container class.
"""
from __future__ import print_function, unicode_literals
from itertools import chain
import json
from subprocess import call

from docker import Client
from six import (
    iteritems,
    iterkeys,
    itervalues,
    text_type,
)
from six.moves import map

from IPython.utils.py3compat import string_types

from IPython.utils.traitlets import (
    Any,
    Dict,
    HasTraits,
    Instance,
    List,
    Type,
    Unicode,
    TraitError,
)


def print_build_output(build_output):
    success = True
    for raw_message in build_output:
        message = json.loads(raw_message)
        try:
            print(message['stream'])
        except KeyError:
            success = False
            print(message['error'])
    return success


def strict_map(func, iterable):
    """
    Python 2/3-agnostic strict map.
    """
    return list(map(func, iterable))


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

    build_path = Unicode(default=None)

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

    ports = Dict(help="Map from container port -> host port.")

    @property
    def open_container_ports(self):
        return strict_map(int, iterkeys(self.ports))

    @property
    def port_bindings(self):
        out = {}
        for key, value in self.ports:
            if isinstance(ports, (list, tuple)):
                key = '/'.join(strict_map(text_type, key))
            out[key] = value
        return out

    # This should really be something like:
    # Either(Instance(str), List(Instance(str)))
    command = Any()

    _client = Any()

    @property
    def client(self):
        if self._client is None:
            self._client = Client()
        return self._client

    def build(self, tag=None):
        """
        Build the container.
        """
        return print_build_output(
            self.client.build(
                self.build_path,
                self.full_imagename(tag=tag),
            )
        )

    def run(self, command=None, tag=None, attach=False):
        """
        Run this container.
        """
        container = self.client.create_container(
            self.full_imagename(tag),
            name=self.name,
            ports=self.open_container_ports,
            volumes=self.volume_mount_points,
            stdin_open=attach,
            tty=attach,
            command=command,
        )

        self.client.start(
            container,
            binds=self.volume_binds,
            port_bindings=self.ports,
            links=self.format_links(),
        )

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
        container = self.client.containers(all=False)
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

    def logs(self, all=False):
        cont = self.instances(all=all)
        return [
            {
                'Id': container['Id'],
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


if __name__ == '__main__':
    cont = Container(image='busybox')
    cont.run()
