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
Run the actual commands to perform the needed actions.
"""

import abc
import subprocess

from typing import List, Optional

from . import config as cconfig
from . import charm as ccharm


class Action(metaclass=abc.ABCMeta):
    """ The base action class. """

    def __init__(self, cfg: cconfig.Config) -> None:
        """ Store the runtime configuration. """
        self._cfg = cfg

    @abc.abstractproperty
    def command(self) -> List[str]:
        """ Return the command to execute. """
        raise NotImplementedError()

    def run(self) -> None:
        """ Run the command or, in no-op mode, just output it. """
        if self._cfg.noop:
            print(' '.join(self.command))
        else:
            subprocess.check_call(self.command, shell=False)


class ActComment(Action):
    """ Output a comment. """

    def __init__(self, cfg: cconfig.Config, text: str) -> None:
        """ Store the comment text. """
        super(ActComment, self).__init__(cfg)
        self._text = text

    @property
    def command(self) -> List[str]:
        """ Output the comment text. """
        return ['printf', '--', '%s', self._text]


class ActDeployCharm(Action):
    """ Deploy a Juju charm, optionally specifying the nodes. """

    def __init__(self,
                 cfg: cconfig.Config,
                 name: str,
                 to: Optional[List[str]] = None) -> None:
        """ Store the charm name. """
        super(ActDeployCharm, self).__init__(cfg)
        self._name = name
        self._to = to

    @property
    def command(self) -> List[str]:
        """ Deploy the charm from the correct directory. """
        cmd = ['juju', 'deploy']

        if self._to is not None:
            cmd.extend([
                '-n', str(len(self._to)),
                '--to', ','.join(self._to),
            ])

        cmd.extend([
            '--',
            ccharm.charm_deploy_dir(self._cfg.basedir,
                                    self._name,
                                    self._cfg.series)
        ])
        return cmd


class ActUpgradeCharm(Action):
    """ Upgrade a Juju charm from the correct directory. """

    def __init__(self, cfg: cconfig.Config, name: str) -> None:
        """ Store the charm name. """
        super(ActUpgradeCharm, self).__init__(cfg)
        self._name = name

    @property
    def command(self) -> List[str]:
        """ Upgrade the charm from the correct directory. """
        return [
            'juju', 'upgrade-charm',
            '--path', ccharm.charm_deploy_dir(self._cfg.basedir,
                                              self._name,
                                              self._cfg.series),
            '--', self._name
        ]


class ActUndeployCharm(Action):
    """ Remove a Juju charm. """

    def __init__(self, cfg: cconfig.Config, name: str) -> None:
        """ Store the charm name. """
        super(ActUndeployCharm, self).__init__(cfg)
        self._name = name

    @property
    def command(self) -> List[str]:
        """ Deploy the charm from the correct directory. """
        return ['juju', 'remove-application', '--', self._name]


class ActAddRelation(Action):
    """ Add a relation between two charms. """

    def __init__(self, cfg: cconfig.Config, src: str, dst: str) -> None:
        """ Store the two endpoints of the relation. """
        super(ActAddRelation, self).__init__(cfg)
        self._src = src
        self._dst = dst

    @property
    def command(self) -> List[str]:
        """ Create the relationship between the two charms. """
        return [
            'juju', 'add-relation', '--', self._src, self._dst
        ]
