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
Utility functions for the StorPool charms management library.
"""

from __future__ import print_function

import abc
import os
import yaml
import subprocess

from typing import Dict, List

from . import config as cconfig


class BranchesError(Exception, metaclass=abc.ABCMeta):
    """ A base class for errors that may occur during parsing. """

    def __init__(self, fname: str, error: Exception) -> None:
        """ Initialize an error object. """
        self._fname = fname
        self._error = error

    @property
    def fname(self) -> str:
        """ Return the name of the invalid file. """
        return self._fname

    @property
    def error(self) -> Exception:
        """ Return the error that occurred. """
        return self._error

    @abc.abstractproperty
    def action(self) -> str:
        """ Return a human-readable name for the action that failed. """
        raise NotImplementedError()

    def __str__(self) -> str:
        """ Provide a human-readable representation of an error. """
        return 'Could not {act} the branches file {fname}: {err}' \
               .format(act=self.action, fname=self.fname, err=self.error)

    def __repr__(self) -> str:
        """ Provide a Python-esque representation of an error. """
        return '{tname}(fname={fname}, error={error})' \
               .format(tname=type(self).__name__, fname=self._fname,
                       error=self._error)


class BranchesReadError(BranchesError):
    """ An error that occurred while reading the branches file. """

    @property
    def action(self) -> str:
        """ This error occurred while reading the branches file. """
        return 'read'


class BranchesParseError(BranchesError):
    """ An error that occurred while parsing the branches file. """

    def action(self) -> str:
        """This error occurred while parsing the branches file. """
        return 'parse'


class BranchesValidateError(BranchesError):
    """ An error that occurred while parsing the branches file. """

    def action(self) -> str:
        """This error occurred while parsing the branches file. """
        return 'validate'


def sp_msg(text: str) -> None:
    """
    Output a message.
    """
    print(text)


def sp_chdir(cfg: cconfig.Config, dirname: str,
             do_chdir: bool = False) -> None:
    """
    Change into the specified directory unless running in no-operation mode.
    Even then, do the chdir() if explicitly asked to.
    """
    if cfg.noop:
        sp_msg("# chdir -- '{dirname}'".format(dirname=dirname))
        if not do_chdir:
            return

    os.chdir(dirname)


def sp_mkdir(cfg: cconfig.Config, dirname: str) -> None:
    """
    Create the specified directory unless running in no-operation mode.
    """
    if cfg.noop:
        sp_msg("# mkdir -- '{dirname}'".format(dirname=dirname))
        return

    os.mkdir(dirname)


def sp_makedirs(cfg: cconfig.Config, dirname: str, mode: int = 0o777,
                exist_ok: bool = False) -> None:
    if cfg.noop:
        sp_msg("# makedirs '{dirname}' mode {mode:04o} exist_ok {exist_ok}"
               .format(dirname=dirname, mode=mode, exist_ok=exist_ok))
        return

    # *Sigh* Python 2 does not have exist_ok, does it now...
    if exist_ok and os.path.isdir(dirname):
        return
    os.makedirs(dirname, mode=mode)


def sp_run(cfg: cconfig.Config, command: List[str]) -> None:
    if cfg.noop:
        sp_msg("# {command}".format(command=' '.join(command)))
        return

    subprocess.check_call(command)


def parse_branches_file(cfg: cconfig.Config) -> Dict[str, str]:
    """ Parse the file containing the list of branches. """
    if cfg.branches_file is None:
        cfg.set_branches({})
        return cfg.branches

    fn = cfg.branches_file  # type: str
    sp_msg('Loading branches information from {fn}'.format(fn=fn))
    try:
        contents = open(fn, mode='r').read()
    except Exception as err:
        raise BranchesReadError(fname=fn, error=err)

    try:
        data = yaml.load(contents)  # type: Dict[str, str]
    except Exception as err:
        raise BranchesParseError(fname=fn, error=err)

    if not isinstance(data, dict):
        raise BranchesValidateError(
            fname=fn,
            error=AttributeError('not a dictionary'))
    if 'branches' not in data:
        raise BranchesValidateError(
            fname=fn,
            error=AttributeError('no "branches" element'))
    if not isinstance(data['branches'], dict):
        raise BranchesValidateError(
            fname=fn,
            error=AttributeError('"branches" not a dictionary'))
    bad = [val for val in data['branches'].items()
           if not (isinstance(val[0], str) and isinstance(val[1], str))]
    if bad:
        raise BranchesValidateError(
            fname=fn,
            error=AttributeError('"branches" not a string:string dictionary'))

    cfg.set_branches(data['branches'])
    return cfg.branches
