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
Helper things to do with charms: check them out, build them, etc.
"""


import collections
import os
import re
import yaml

from typing import Callable, Dict, List, Optional

from . import config as cconfig
from . import git as cgit
from . import utils as cu


_TYPING_USED = (Dict,)


RE_ELEM = re.compile('(?P<type> (?: layer | interface ) ) : '
                     '(?P<name> [a-z][a-z-]* ) $',
                     re.X)


Element = collections.namedtuple('Element', [
    'name',
    'type',
    'parent_dir',
    'fname',
    'exists',
])


class CharmError(Exception):
    """ A base class for charm-related errors. """

    def __init__(self, message: str) -> None:
        """ Initialize a charm error object. """
        super(CharmError, self).__init__(message)


def parse_layers(cfg: cconfig.Config,
                 name: str,
                 to_process: List[Element],
                 layers_required: bool) -> None:
    if cfg.noop:
        cu.sp_msg('(would examine the "layer.yaml" file and '
                  'process layers and interfaces recursively)')
        return

    try:
        with open('layer.yaml', mode='r') as f:
            contents = yaml.load(f)
    except Exception as err:
        if isinstance(err, FileNotFoundError) and not layers_required:
            return
        raise CharmError(
            'Could not load the layer.yaml file from {name}: {err}'
            .format(name=name, err=err))

    for elem in contents['includes']:
        if elem.find('storpool') == -1 and elem != 'interface:cinder-backend':
            continue
        m = RE_ELEM.match(elem)
        if m is None:
            raise CharmError(
                'Invalid value "{elem}" in the {name} "includes" directive!'
                .format(name=name, elem=elem))
        (e_type, e_name) = (m.groupdict()['type'], m.groupdict()['name'])

        parent_dir = '../{t}s'.format(t=e_type)
        fname = '{t}-{n}'.format(t=e_type, n=e_name)
        dname = '{parent}/{fname}'.format(parent=parent_dir, fname=fname)
        exists = os.path.exists(dname)
        if exists and not os.path.isdir(dname):
            raise CharmError(
                'Something named {dname} exists and it is not a directory!'
                .format(dname=dname))
        to_process.append(Element(
            name=e_name,
            type=e_type,
            parent_dir=parent_dir,
            fname=fname,
            exists=exists,
        ))


def checkout_element(cfg: cconfig.Config,
                     name: str,
                     to_process: List[Element],
                     layers_required: bool = False) -> None:
    """
    Check out a single charm, interace, or layer, then look at
    its configuration to find the elements it depends on.
    """
    cgit.checkout(cfg, name)
    cu.sp_chdir(cfg, name)
    parse_layers(cfg, name, to_process, layers_required)
    cu.sp_chdir(cfg, '../../charms')


def recurse(cfg: cconfig.Config,
            charm_names: List[str],
            process_charm: Callable[[str, List[Element]], None],
            process_element: Optional[Callable[[cconfig.Config,
                                                Element,
                                                List[Element]],
                                               None]]
            ) -> None:
    """
    Recursively process a charm, its layers, its interfaces,
    their layers, their interfaces, etc.
    """
    cu.sp_chdir(cfg, 'charms')

    to_process = []  # type: List[Element]
    for name in charm_names:
        process_charm(name, to_process)
    if process_element is None:
        return

    processed = {}  # type: Dict[str, Element]
    while True:
        if not to_process:
            cu.sp_msg('No more layers or interfaces to process')
            break
        processing = {
            elem.fname: elem for elem in to_process
            if elem.fname not in processed and not elem.exists
        }.values()
        to_process = []
        for elem in processing:
            cu.sp_chdir(cfg, elem.parent_dir)
            process_element(cfg, elem, to_process)
            processed[elem.fname] = elem


def charm_build_dir(basedir: str, name: str, series: str) -> str:
    return '{base}/built/{series}/{name}'.format(base=basedir,
                                                 series=series,
                                                 name=name)


def charm_deploy_dir(basedir: str, name: str, series: str) -> str:
    return '{build}/{series}/{name}' \
        .format(build=charm_build_dir(basedir, name, series),
                series=series,
                name=name)


def checkout_all(cfg: cconfig.Config, charm_names: List[str]) -> None:
    """ Check out all the StorPool charms into the subdirectories. """
    try:
        cu.sp_chdir(cfg, cfg.basedir)
    except FileNotFoundError:
        raise CharmError('The {d} directory does not seem to exist!'
                         .format(d=cfg.basedir))

    cu.parse_branches_file(cfg)

    cu.sp_msg('Recreating the {subdir}/ tree'.format(subdir=cfg.subdir))
    cu.sp_run(cfg, ['rm', '-rf', '--', cfg.subdir])
    cu.sp_mkdir(cfg, cfg.subdir)
    cu.sp_chdir(cfg, cfg.subdir)
    for comp in ('layers', 'interfaces', 'charms'):
        cu.sp_mkdir(cfg, comp)

    def process_charm(name: str, to_process: List[Element]) -> None:
        cu.sp_msg('Checking out the {name} charm'.format(name=name))
        checkout_element(cfg, name, to_process, layers_required=True)
        processed.append('charms/' + name)

    def process_element(cfg: cconfig.Config,
                        elem: Element,
                        to_process: List[Element]) -> None:
        cu.sp_msg('Checking out the {name} {type}'
                  .format(name=elem.name, type=elem.type))
        checkout_element(cfg, elem.fname, to_process)
        processed.append(elem.type + 's/' + elem.fname)

    processed = []  # type: List[str]
    recurse(cfg, charm_names, process_charm, process_element)

    cu.sp_msg('The StorPool charms were checked out into {basedir}/{subdir}'
              .format(basedir=cfg.basedir, subdir=cfg.subdir))
    cu.sp_msg('')


def build_all(cfg: cconfig.Config, charm_names: List[str]) -> None:
    """ Build all the StorPool charms (already checked out). """
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=cfg.subdir)
    cu.sp_msg('Building the charms in the {d} directory'.format(d=subdir_full))
    try:
        cu.sp_chdir(cfg, subdir_full, do_chdir=True)
    except FileNotFoundError:
        raise CharmError(
            'The {subdir} directory does not seem to exist!'
            .format(subdir=subdir_full))
    basedir = os.getcwd()

    def process_charm(name: str, to_process: List[Element]) -> None:
        """ Build a single charm. """
        cu.sp_msg('Building the {name} charm'.format(name=name))
        cu.sp_chdir(cfg, name)
        short_name = name.replace('charm-', '')
        build_dir = charm_build_dir(basedir, short_name, cfg.series)
        cu.sp_msg('- recreating the build directory')
        cu.sp_run(cfg, ['rm', '-rf', '--', build_dir])
        cu.sp_makedirs(cfg, build_dir, mode=0o755)
        cu.sp_msg('- building the charm')
        cu.sp_run(cfg, [
            'env',
            'LAYER_PATH={basedir}/layers'.format(basedir=basedir),
            'INTERFACE_PATH={basedir}/interfaces'.format(basedir=basedir),
            'charm', 'build', '-s', cfg.series, '-n', short_name,
            '-o', build_dir
        ])
        cu.sp_chdir(cfg, '../')

    recurse(cfg, charm_names, process_charm, None)
    cu.sp_msg('The StorPool charms were built in {subdir}'
              .format(subdir=subdir_full))
    cu.sp_msg('')
