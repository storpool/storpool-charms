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
Helper routines for accessing the Juju cluster.
"""


import abc
import subprocess

import json
import yaml

from typing import cast, Any, Dict, List, Optional, Set

from . import actions as cact
from . import config as cconfig
from . import data as cdata


_TYPING_USED = (Optional,)


STORAGE_CHARMS = ('cinder',)


COMPUTE_CHARMS = ('nova-compute', 'nova-compute-kvm',)


class Error(Exception):
    """ A base class for Juju-related errors. """

    pass


class CommandError(Error, metaclass=abc.ABCMeta):
    """ An error that occurred while running a Juju command. """

    def __init__(self, cmd: str, error: Exception) -> None:
        """ Store the error info. """
        self._cmd = cmd
        self._error = error

    @property
    def command(self) -> str:
        """ Return the command that failed. """
        return self._cmd

    @property
    def error(self) -> Exception:
        """ Return the error that failed. """
        return self._error

    @abc.abstractproperty
    def action(self) -> str:
        raise NotImplementedError()

    def __str__(self) -> str:
        """ Provide a human-readable error description. """
        return 'Could not {act} the {cmd} command: {error}' \
               .format(act=self.action, cmd=self.command, error=self.error)

    def __repr__(self) -> str:
        """ Provide a Python-esque representation. """
        return '{tname}(cmd={cmd}, error={error})' \
               .format(tname=type(self).__name__,
                       cmd=repr(self._cmd), error=repr(self._error))


class RunError(CommandError):
    """ An error that occurred while running the command. """

    @property
    def action(self) -> str:
        """ The error occurred while running the command. """
        return 'run'


class DecodeError(CommandError):
    """ An error that occurred while decoding the command's output. """

    @property
    def action(self) -> str:
        """ The error occurred while decoding the command's output. """
        return 'decode the output of'


class StorPoolError(CommandError):
    """ An error that occurred while making StorPool-specific adjustments. """

    @property
    def action(self) -> str:
        """ StorPool-specific. """
        return 'make the StorPool adjustments for'


def add_storpool_status(res: cdata.Status) -> None:
    """ Run some StorPool-specific heuristics. """
    meta_apps = res['_meta']['applications']
    meta_sp = res['_meta']['sp']

    def find_charm(ctype: str, apps: Dict[str, cdata.Application]) -> str:
        """ Find the charm to use of the specified type. """
        found_charm = None
        for name, app in apps.items():
            cname = app['_name']
            if not app['units']:
                continue

            if found_charm is None:
                found_charm = cname
                continue

            assert found_charm == cname, \
                'more than one {ctype} charm: {old} and {new}' \
                .format(ctype=ctype, old=found_charm, new=cname)

        if found_charm is None:
            raise StorPoolError(
                'status',
                Exception('could not find a {ctype} charm'
                          .format(ctype=ctype)))

        return found_charm

    def find_real_machines(ctype: str, charm: str) -> Set[str]:
        """ Get the bare-metal machines for the specified charm. """
        mids = set()  # type: Set[str]
        for unit in res['applications'][charm]['units'].values():
            mach = cast(cdata.Container, unit['_mach'])
            if mach['_mtype'] == 'container':
                mids.add(mach['_mach']['_mid'])
            else:
                mids.add(mach['_mid'])
        return mids

    meta_sp['chosen_charm'].update({
        ctype: find_charm(ctype, apps)
        for ctype, apps in meta_apps['by_type'].items()
    })
    missing = set(meta_sp['chosen_charm'].keys()) - \
        set(['compute', 'storage'])
    if missing:
        raise StorPoolError('status',  Exception(
            'Could not find some charms: ' + ' '.join(missing)))

    cmachines = {
        ctype: find_real_machines(ctype, charm)
        for ctype, charm in meta_sp['chosen_charm'].items()
    }

    cmachines['candleholder'] = cmachines['storage'] - cmachines['compute']
    cmachines['compute'] = cmachines['compute'] - cmachines['candleholder']

    del cmachines['storage']
    assert cmachines['compute']
    if not cmachines['candleholder']:
        del cmachines['candleholder']

    meta_sp['machines'].update({
        ctype: sorted(machines)
        for ctype, machines in cmachines.items()
    })


def get_status(add_sp: bool = True) -> cdata.Status:
    """ Get the "juju status" output. """
    try:
        status_j = subprocess.check_output(['juju', 'status', '--format=json'])
    except Exception as err:  # pylint: disable=broad-except
        raise RunError('status', err)

    try:
        data = json.loads(status_j.decode('UTF-8'))
        assert isinstance(data, dict), 'not a JSON object'
        res = cast(cdata.Status, data)

        # Now define some more metadata linkages
        res['_meta'] = cast(cdata.SPStatusMeta, {
            'applications': cast(cdata.SPStatusMetaApps, {
                'by_charm': {},
                'by_type': {},
                'chosen_charm': {},
            }),

            'machines': cast(cdata.SPStatusMetaMachines, {
                'all': {},
                'by_type': {},
            }),

            'sp': cast(cdata.SPStatusStorPool, {
                'chosen_charm': {},
                'machines': {},
                'targets': {}
            }),
        })
        meta = res['_meta']
        meta_apps = meta['applications']
        meta_mach = meta['machines']

        for mid, mach in res['machines'].items():
            mach['_mid'] = mid
            mach['_mtype'] = 'machine'
            mach['_type'] = None
            mach['_units'] = {}

            assert mid not in meta_mach['all'], 'duplicate machine ' + mid
            meta_mach['all'][mid] = mach

            for cid, cont in mach.get('containers', {}).items():
                cont['_mid'] = cid
                cont['_mtype'] = 'container'
                cont['_type'] = None
                cont['_mach'] = mach
                cont['_units'] = {}

                assert cid not in meta_mach['all'], \
                    'duplicate container ' + cid
                meta_mach['all'][cid] = cont

        for name, app in res['applications'].items():
            app['_name'] = name
            charm = app['charm-name']
            if charm not in meta_apps['by_charm']:
                meta_apps['by_charm'][charm] = {}
            meta_apps['by_charm'][charm][name] = app

            if charm in STORAGE_CHARMS:
                ctype = 'storage'  # type: Optional[str]
            elif charm in COMPUTE_CHARMS:
                ctype = 'compute'
            else:
                ctype = None
            app['_type'] = ctype
            if ctype is not None:
                if ctype not in meta_apps['by_type']:
                    meta_apps['by_type'][ctype] = {}
                meta_apps['by_type'][ctype][name] = app

            for uname, unit in app.get('units', {}).items():
                unit['_name'] = uname
                unit['_app'] = app

                mid = unit['machine']
                # Bah, union types, am I right?
                umach = cast(cdata.Container, meta_mach['all'][mid])
                unit['_mach'] = umach
                umach['_units'][uname] = unit

                if ctype is not None:
                    if umach['_type'] is not None:
                        assert umach['_type'] == ctype, \
                            'machine {mid} used for both storage and compute' \
                            .format(mach=mid)
                    else:
                        umach['_type'] = ctype

                    if ctype not in meta_mach['by_type']:
                        meta_mach['by_type'][ctype] = {}
                    if mid not in meta_mach['by_type'][ctype]:
                        meta_mach['by_type'][ctype][mid] = umach

    except (ValueError, AssertionError) as err:
        raise DecodeError('status', err)

    if add_sp:
        add_storpool_status(res)

    return res


def get_deploy_actions(cfg: cconfig.Config,
                       status: cdata.Status) -> List[cact.Action]:
    """ Deploy the charms and add the relations. """
    actions = [
        cact.ActComment(cfg, 'Deploying the storpool-block charm'),
        cact.ActDeployCharm(cfg, 'storpool-block'),
    ]

    nova_charm = status['_meta']['sp']['chosen_charm']['compute']
    actions.extend([
        cact.ActComment(
            cfg,
            'Linking the storpool-block charm with the {nova} charm'
           .format(nova=nova_charm)),
        cact.ActAddRelation(
            cfg,
            nova_charm + ':juju-info',
            'storpool-block:juju-info'),
    ])

    if 'candleholder' in status['_meta']['sp']['machines']:
        machines = status['_meta']['sp']['machines']['candleholder']
        actions.extend([
            cact.ActComment(
                cfg,
                'Deploying the storpool-candleholder charm to {machines}'
               .format(machines=', '.join(machines))),
            cact.ActDeployCharm(
                cfg,
                'storpool-candleholder', to=machines),
            cact.ActComment(
                cfg,
                'Linking the storpool-candleholder charm with '
                'the storpool-block charm'),
            cact.ActAddRelation(
                cfg,
                'storpool-candleholder:juju-info',
                'storpool-block:juju-info'),
        ])
    else:
        actions.append(cact.ActComment(
            cfg,
            'Apparently Cinder and Nova are on the same machines; '
            'skipping the storpool-candleholder deployment'))

    actions.extend([
        cact.ActComment(
            cfg,
            'Deploying the cinder-storpool charm'),
        cact.ActDeployCharm(
            cfg,
            'cinder-storpool'),
    ])

    cinder_charm = status['_meta']['sp']['chosen_charm']['storage']
    actions.extend([
        cact.ActComment(
            cfg,
            'Linking the cinder-storpool charm with the {cinder} charm'
            .format(cinder=cinder_charm)),
        cact.ActAddRelation(
            cfg,
            '{cinder}:storage-backend'.format(cinder=cinder_charm),
            'cinder-storpool:storage-backend'),

        cact.ActComment(
            cfg,
            'Linking the cinder-storpool charm with the storpool-block charm'),
        cact.ActAddRelation(
            cfg,
            'storpool-block:storpool-presence',
            'cinder-storpool:storpool-presence'),

        cact.ActComment(
            cfg,
            'The StorPool charms were deployed from {basedir}/{subdir}'
            .format(basedir=cfg.basedir, subdir=cfg.subdir)),
        cact.ActComment(
            cfg,
            ''),
    ])

    return actions


def get_undeploy_actions(cfg: cconfig.Config,
                         names: List[str]) -> List[cact.Action]:
    """ Undeploy the charms; the relations are automatically removed. """
    actions = []
    for name in names:
        actions.extend([
            cact.ActComment(
                cfg,
                'Removing the {name} Juju application'.format(name=name)),
            cact.ActUndeployCharm(
                cfg,
                name),
        ])

    actions.extend([
        cact.ActComment(
            cfg,
            'Removed {count} StorPool charms'.format(count=len(names))),
        cact.ActComment(
            cfg,
            ''),
    ])

    return actions


def get_upgrade_actions(cfg: cconfig.Config,
                        names: List[str]) -> List[cact.Action]:
    """ Upgrade the charms from their respective directories. """
    actions = []
    for name in names:
        actions.extend([
            cact.ActComment(
                cfg,
                'Upgrading the {name} Juju application'.format(name=name)),
            cact.ActUpgradeCharm(
                cfg,
                name),
        ])

    actions.extend([
        cact.ActComment(
            cfg,
            'Upgraded {count} StorPool charms'.format(count=len(names))),
        cact.ActComment(
            cfg,
            ''),
    ])

    return actions


def juju_ssh_single_line(cmd: List[str]) -> str:
    """ Get the first non-empty line from a command's output. """
    output = subprocess.check_output(cmd).decode('UTF-8')
    lines = output.split('\n')
    for line in lines:
        stripped = line.strip()  # type: str
        if stripped:
            return stripped
    return ''


def get_storpool_config_data(cfg: cconfig.Config,
                             status: cdata.Status) -> Dict[str,
                                                           Dict[str, str]]:
    """ Generate the key/value per-machine config sections. """
    def correct_space(ifdata: cdata.Interface) -> bool:
        """ Check whether this interface is in the correct space. """
        return ifdata.get('space', None) == cfg.space

    targets = set()  # type: Set[str]
    for machine_names in status['_meta']['sp']['machines'].values():
        targets.update(machine_names)

    res = {}  # type: Dict[str, Dict[str, str]]
    seen_hostnames = {}  # type: Dict[str, str]
    for (oid, tgt) in enumerate(sorted(targets)):
        name = juju_ssh_single_line(['juju', 'ssh', tgt, 'hostname'])
        if name in seen_hostnames:
            raise StorPoolError('storpool-config', Exception(
                'Hostname "{name}" seen on both machines {old} and {new}'
                .format(name=name, old=seen_hostnames[name], new=tgt)))
        seen_hostnames[name] = tgt

        mach = status['machines'][tgt]
        ifaces = [iface[0]
                  for iface in mach['network-interfaces'].items()
                  if correct_space(iface[1])]
        if not ifaces:
            raise StorPoolError('storpool-config', Exception(
                'Could not find any "{sp}" interfaces on {name} ({tgt}, {a})'
                .format(sp=cfg.space, name=name, tgt=tgt, a=mach['dns-name'])))
        res[name] = {
            'SP_OURID': str(oid + 40),
            'SP_IFACE': ','.join(ifaces),
        }

    return res


def get_storpool_config(cfg: cconfig.Config, status: cdata.Status) -> str:
    if not cfg.space:
        raise StorPoolError('storpool-config',
                            Exception('No StorPool space (-S) specified'))

    res = """
# Autogenerated StorPool test configuration

SP_CLUSTER_NAME=Juju charms test cluster
SP_CLUSTER_ID=a.a

SP_EXPECTED_NODES=3
SP_NODE_NON_VOTING=1
"""

    for name, data in get_storpool_config_data(cfg, status).items():
        res += """
[{name}]
SP_OURID={oid}
SP_IFACE={ifaces}
""".format(name=name, oid=data['SP_OURID'], ifaces=data['SP_IFACE'])

    return res


def get_charm_config_data(cfg: cconfig.Config,
                          status: cdata.Status,
                          conf: str,
                          bypass: List[str]) -> Dict[str, Dict[str, Any]]:
    if cfg.repo_auth is None:
        raise StorPoolError('charm-config', Exception(
            'no StorPool PPA authentication info provided'))

    storage = status['_meta']['machines']['by_type']['storage'].keys()
    cinder_in_lxd = bool([mid for mid in storage if '/lxd/' in mid])

    ch = {
        'storpool-block': {
            'handle_lxc': cinder_in_lxd,
            'storpool_version': '18.01',
            'storpool_openstack_version': '1.5.0-1~1ubuntu1',
            'storpool_repo_url':
            'http://{auth}@repo.storpool.com/storpool-maas/'
            .format(auth=cfg.repo_auth),
            'storpool_conf': conf,
        },
        'cinder-storpool': {
            'storpool_template': 'hybrid-r3',
        },
    }  # type: Dict[str, Dict[str, Any]]

    if bypass:
        ch['storpool-block']['bypassed_checks'] = ','.join(sorted(bypass))
        ch['cinder-storpool']['bypassed_checks'] = ','.join(sorted(bypass))

    return ch


def get_charm_config(cfg: cconfig.Config,
                     status: cdata.Status,
                     conf: str,
                     bypass: List[str]) -> str:
    return cast(str,
                yaml.dump(get_charm_config_data(cfg, status, conf, bypass),
                          default_flow_style=False))
