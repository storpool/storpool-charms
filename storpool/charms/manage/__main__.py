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


from __future__ import print_function

import argparse
import os

from typing import List

from . import charm as ccharm
from . import config as cconfig
from . import juju as cjuju
from . import utils as cu


charm_names = [
    'charm-cinder-storpool',
    'charm-storpool-block',
    'charm-storpool-candleholder',
]


def test_element(cfg: cconfig.Config) -> None:
    if os.path.isfile('tox.ini'):
        cu.sp_msg('- running pep8/flake8 through tox')
        cu.sp_run(cfg, ['tox', '-e', 'pep8'])
        cu.sp_msg('- running all the tox tests')
        cu.sp_run(cfg, ['tox', '-e', 'ALL'])
        # Sigh... the build gets confused.  A lot.
        cu.sp_msg('- removing the .tox/ directory')
        cu.sp_run(cfg, ['rm', '-rf', '.tox/'])
    else:
        cu.sp_msg('- no tox.ini file, running some tests by ourselves')
        cu.sp_msg('- running flake8')
        cu.sp_run(cfg, ['flake8', '.'])
        cu.sp_msg('- running pep8')
        cu.sp_run(cfg, ['pep8', '.'])


def test_elements(cfg: cconfig.Config, paths: List[str]) -> None:
    for path in paths:
        print('\n===== Testing {path}\n'.format(path=path))
        cu.sp_chdir(cfg, '../' + path)
        test_element(cfg)
        cu.sp_chdir(cfg, '../')


def cmd_checkout(cfg: cconfig.Config) -> None:
    ccharm.checkout_all(cfg, charm_names)


def cmd_pull(cfg: cconfig.Config) -> None:
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=cfg.subdir)
    cu.sp_msg('Updating the charms in the {d} directory'.format(d=subdir_full))
    try:
        cu.sp_chdir(cfg, subdir_full)
    except FileNotFoundError:
        exit('The {d} directory does not seem to exist!'
             .format(d=subdir_full))

    def process_element(cfg: cconfig.Config,
                        elem: ccharm.Element,
                        to_process: List[ccharm.Element]) -> None:
        cu.sp_msg('Updating the {name} {type}'
                  .format(name=elem.name, type=elem.type))
        cu.sp_chdir(cfg, elem.fname)
        cu.sp_run(cfg, ['git', 'pull', '--ff-only'])
        ccharm.parse_layers(cfg, elem.name, to_process, False)
        processed.append(elem.type + 's/' + elem.fname)
        cu.sp_chdir(cfg, '../')

    def process_charm(name: str, to_process: List[ccharm.Element]) -> None:
        elem = ccharm.Element(
            name=name,
            type='charm',
            parent_dir='',
            fname=name,
            exists=True,
        )
        process_element(cfg, elem, to_process)

    processed = []  # type: List[str]
    ccharm.recurse(cfg, charm_names, process_charm, process_element)

    cu.sp_msg('The StorPool charms were updated in {subdir}'
              .format(subdir=subdir_full))
    cu.sp_msg('')


def cmd_test(cfg: cconfig.Config) -> None:
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=cfg.subdir)
    cu.sp_msg('Running tox tests for the charms in the {d} directory'
              .format(d=subdir_full))
    try:
        cu.sp_chdir(cfg, subdir_full)
    except FileNotFoundError:
        exit('The {d} directory does not seem to exist!'
             .format(d=subdir_full))

    def process_element(cfg: cconfig.Config,
                        elem: ccharm.Element,
                        to_process: List[ccharm.Element]) -> None:
        cu.sp_msg('Examining the {name} {type}'
                  .format(name=elem.name, type=elem.type))
        cu.sp_chdir(cfg, elem.fname)
        ccharm.parse_layers(cfg, elem.name, to_process, False)
        processed.append(elem.type + 's/' + elem.fname)
        cu.sp_chdir(cfg, '../')

    def process_charm(name: str, to_process: List[ccharm.Element]) -> None:
        elem = ccharm.Element(
            name=name,
            type='charm',
            parent_dir='',
            fname=name,
            exists=True,
        )
        process_element(cfg, elem, to_process)

    processed = []  # type: List[str]
    ccharm.recurse(cfg, charm_names, process_charm, process_element)

    cu.sp_msg('Running the tox tests for {count} elements'
              .format(count=len(processed)))
    test_elements(cfg, sorted(processed))

    cu.sp_msg('The StorPool charms were tested in {subdir}'
              .format(subdir=subdir_full))
    cu.sp_msg('')


def cmd_build(cfg: cconfig.Config) -> None:
    ccharm.build_all(cfg, charm_names)


def cmd_deploy(cfg: cconfig.Config) -> None:
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=cfg.subdir)
    cu.sp_msg('Deploying the charms from the {d} directory'
              .format(d=subdir_full))
    try:
        cu.sp_chdir(cfg, subdir_full, do_chdir=True)
    except FileNotFoundError:
        exit('The {d} directory does not seem to exist!'
             .format(d=subdir_full))

    short_names = [name.replace('charm-', '') for name in charm_names]

    cu.sp_msg('Obtaining the current Juju status')
    status = cjuju.get_status()
    found = [name for name in short_names if name in status['applications']]
    if found:
        exit('Found some StorPool charms already installed: {found}'
             .format(found=', '.join(found)))

    for action in cjuju.get_deploy_actions(cfg, status):
        action.run()


def cmd_undeploy(cfg: cconfig.Config) -> None:
    short_names = [name.replace('charm-', '') for name in charm_names]

    cu.sp_msg('Obtaining the current Juju status')
    status = cjuju.get_status()
    found = [name for name in short_names if name in status['applications']]
    if not found:
        exit('No StorPool charms are installed')
    else:
        cu.sp_msg('About to remove {count} StorPool charms'
                  .format(count=len(found)))

    for action in cjuju.get_undeploy_actions(cfg, found):
        action.run()


def cmd_upgrade(cfg: cconfig.Config) -> None:
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=cfg.subdir)
    cu.sp_msg('Upgrading the charms from the {d} directory'
              .format(d=subdir_full))
    try:
        cu.sp_chdir(cfg, subdir_full, do_chdir=True)
    except FileNotFoundError:
        exit('The {d} directory does not seem to exist!'
             .format(d=subdir_full))

    short_names = [name.replace('charm-', '') for name in charm_names]

    cu.sp_msg('Obtaining the current Juju status')
    status = cjuju.get_status()
    found = [name for name in short_names if name in status['applications']]
    if not found:
        exit('No StorPool charms are installed')
    else:
        cu.sp_msg('About to upgrade {count} StorPool charms'
                  .format(count=len(found)))

    for action in cjuju.get_upgrade_actions(cfg, found):
        action.run()


def cmd_generate_config(cfg: cconfig.Config) -> None:
    status = cjuju.get_status()
    print(cjuju.get_storpool_config(cfg, status))


def cmd_generate_charm_config(cfg: cconfig.Config) -> None:
    if cfg.repo_auth is None:
        exit('No repository username:password (-A) specified')
    status = cjuju.get_status()
    conf = cjuju.get_storpool_config(cfg, status=status)
    charmconf = cjuju.get_charm_config(cfg, status, conf, [])
    print(charmconf)


COMMANDS = {
    'build': cmd_build,
    'deploy': cmd_deploy,
    'checkout': cmd_checkout,
    'pull': cmd_pull,
    'undeploy': cmd_undeploy,
    'upgrade': cmd_upgrade,
    'generate-config': cmd_generate_config,
    'generate-charm-config': cmd_generate_charm_config,
    'test': cmd_test,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='storpool-charms',
        usage='''
        storpool-charms [-N] [-d basedir] [-s series] deploy
        storpool-charms [-N] [-d basedir] [-s series] upgrade
        storpool-charms [-N] [-d basedir] undeploy

        storpool-charms [-N] -S storpool-space generate-config
        storpool-charms [-N] -S storpool-space -A repo_auth \
generate-charm-config

        storpool-charms [-N] [-B branches-file] [-d basedir] checkout
        storpool-charms [-N] [-d basedir] pull
        storpool-charms [-N] [-d basedir] test
        storpool-charms [-N] [-d basedir] [-s series] build

    The "-A repo_auth" option accepts a repo_username:repo_password parameter.

    A {subdir} directory will be created in the specified base directory.
    For the "checkout" and "pull" commands, specifying "-X tox" will not run
    the automated tests immediately after everything has been updated.'''
        .format(subdir=cconfig.DEFAULT_SUBDIR),
    )
    parser.add_argument('-d', '--basedir', default=cconfig.DEFAULT_BASEDIR,
                        help='specify the base directory for the charms tree')
    parser.add_argument('-N', '--noop', action='store_true',
                        help='no-operation mode, display what would be done')
    parser.add_argument('-s', '--series', default=cconfig.DEFAULT_SERIES,
                        help='specify the name of the series to build for')
    parser.add_argument('-S', '--space',
                        help='specify the name of the StorPool network space')
    parser.add_argument('-U', '--baseurl', default=cconfig.DEFAULT_BASEURL,
                        help='specify the base URL for the StorPool Git '
                        'repositories')
    parser.add_argument('-X', '--skip',
                        help='specify stages to skip during the deploy test')
    parser.add_argument('-A', '--repo-auth',
                        help='specify the StorPool repository '
                        'authentication data')
    parser.add_argument('-B', '--branches-file',
                        help='specify the YAML file listing the branches to '
                             'check out')
    parser.add_argument('command', choices=sorted(COMMANDS.keys()))

    args = parser.parse_args()
    cfg = cconfig.Config(
        basedir=args.basedir,
        baseurl=args.baseurl,
        branches_file=args.branches_file,
        noop=args.noop,
        series=args.series,
        space=args.space,
        skip=args.skip,
        repo_auth=args.repo_auth,
    )
    COMMANDS[args.command](cfg)


if __name__ == '__main__':
    main()
