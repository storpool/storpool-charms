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
Configuration information for the StorPool charms management library.
"""

from typing import Dict, Optional


DEFAULT_BASEDIR = '.'
DEFAULT_SUBDIR = 'storpool-charms'
DEFAULT_BASEURL = 'https://github.com/storpool'
DEFAULT_SERIES = 'xenial'


class Config(object):
    """ Hold configuration information about a spcharms run. """

    def __init__(self,
                 basedir: str = DEFAULT_BASEDIR,
                 subdir: str = DEFAULT_SUBDIR,
                 baseurl: str = DEFAULT_BASEURL,
                 branches_file: Optional[str] = None,
                 noop: bool = False,
                 series: str = DEFAULT_SERIES,
                 space: Optional[str] = None,
                 skip: Optional[str] = None,
                 repo_auth: Optional[str] = None) -> None:
        """ Initialize a configuration object. """
        self._basedir = basedir
        self._subdir = subdir
        self._baseurl = baseurl
        self._branches_file = branches_file
        self._noop = noop
        self._series = series
        self._space = space
        self._skip = skip
        self._repo_auth = repo_auth

        self._branches = {}  # type: Dict[str, str]

    @property
    def basedir(self) -> str:
        """ Return the directory to create the subdirectory in. """
        return self._basedir

    @property
    def subdir(self) -> str:
        """ Return the subdirectory for the charms hierarchy. """
        return self._subdir

    @property
    def baseurl(self) -> str:
        """ Return the URL to checkout the charms from. """
        return self._baseurl

    @property
    def branches_file(self) -> Optional[str]:
        """ Return the name of the file listing the branches to use. """
        return self._branches_file

    @property
    def noop(self) -> bool:
        """ Return the no-operation flag. """
        return self._noop

    @property
    def series(self) -> str:
        """ Return the charm series to build for. """
        return self._series

    @property
    def space(self) -> Optional[str]:
        """ Return the network space to configure for. """
        return self._space

    @property
    def skip(self) -> Optional[str]:
        """ Return the list of charms, layers, or interfaces to skip. """
        return self._skip

    @property
    def repo_auth(self) -> Optional[str]:
        """ Return the StorPool PPA authentication string. """
        return self._repo_auth

    @property
    def branches(self) -> Dict[str, str]:
        """ Return a copy of the parsed dictionary of branches. """
        return dict(self._branches)

    def set_branches(self, branches: Dict[str, str]) -> None:
        """ Set the parsed dictionary of branches. """
        self._branches = branches
