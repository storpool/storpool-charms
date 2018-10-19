#!/usr/bin/python3
#
# Copyright (c) 2018  StorPool
# All rights reserved.
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

"""
Packaging metadata for the storpool.charms.manage library.
"""


import re
import setuptools


RE_VERSION = r'''^
    \s* VERSION \s* = \s* '
    (?P<version>
           (?: 0 | [1-9][0-9]* )    # major
        \. (?: 0 | [1-9][0-9]* )    # minor
        \. (?: 0 | [1-9][0-9]* )    # patchlevel
    (?: \. [a-zA-Z0-9]+ )?          # optional addendum (dev1, beta3, etc.)
    )
    ' \s*
    $'''


def get_version():
    """ Get the module version from its __init__.py file. """
    found = None
    re_semver = re.compile(RE_VERSION, re.X)
    with open('storpool/charms/manage/__init__.py') as verfile:
        for line in verfile.readlines():
            match = re_semver.match(line)
            if not match:
                continue
            assert found is None
            found = match.group('version')

    assert found is not None
    return found


def get_long_description():
    """ Read the long description from the README.md file. """
    with open('README.md') as descfile:
        return descfile.read()


setuptools.setup(
    name='storpool_charms_manage',
    version=get_version(),
    install_requires=['mypy_extensions', 'PyYAML'],

    description='Build, deploy, and configure the StorPool Juju charms',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',

    author='Peter Pentchev',
    author_email='openstack-dev@storpool.com',
    url='https://github.com/storpool/storpool-charms/',

    packages=('storpool', 'storpool.charms', 'storpool.charms.manage'),
    namespace_packages=('storpool', 'storpool.charms'),
    package_data={
        'storpool.charms.manage': [
            # The typed module marker
            'py.typed',
        ],
    },

    license='BSD-2',
    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',

        'License :: DFSG approved',
        'License :: Freely Distributable',
        'License :: OSI Approved :: Apache Software License',

        'Operating System :: POSIX',
        'Operating System :: Unix',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',

        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],

    entry_points={
        'console_scripts': [
            'spcharms_manage=storpool.charms.manage.__main__:main',
        ],
    },

    zip_safe=True,
)
