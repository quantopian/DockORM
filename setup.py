#!/usr/bin/env python
#
# Copyright 2014 Quantopian, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from setuptools import setup

install_requires = []
with open('requirements.txt') as f:
    for line in f.readlines():
        req = line.strip()
        if not req or req.startswith(('-e', '#')):
            continue
        install_requires.append(req)


setup_args = dict(
    name='DockORM',
    version='0.0.1',
    description='An object-relational mapper for Docker containers.',
    author='Quantopian Inc.',
    author_email='ssanderson@quantopian.com',
    packages=['dockorm'],
    license='Apache 2.0',
    zip_safe=False,
    classifiers=[
        'Framework :: IPython',
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
    ],
    install_requires=install_requires,
    url="https://github.com/quantopian/dockrm",
)


def main():
    setup(**setup_args)


if __name__ == '__main__':
    main()
