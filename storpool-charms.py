#!/usr/bin/python

from __future__ import print_function

import argparse
import collections
import json
import os
import re
import requests
import subprocess
import tempfile
import time
import yaml
import six

baseurl = 'https://github.com/storpool'
subdir = 'storpool-charms'
charm_data = \
    {
        'charm-cinder-storpool':
        {
            'status':
            [
                'waiting for the StorPool block presence data',
                'waiting for the StorPool configuration',
                'the StorPool Cinder backend should be up and running',
                'the StorPool Cinder backend should be up and running',
            ],
        },

        'charm-storpool-block':
        {
            'status':
            [
                'waiting for the StorPool configuration',
                'so far so good so what',
                'so far so good so what',
                'so far so good so what',
            ],
        },

        'charm-storpool-candleholder':
        {
            'status':
            [
                'bring on the subordinate charms!',
                'bring on the subordinate charms!',
                'bring on the subordinate charms!',
                'bring on the subordinate charms!',
            ],
        },
    }
charm_names = sorted(charm_data.keys())
re_elem = re.compile('(?P<type> (?: layer | interface ) ) : '
                     '(?P<name> [a-z][a-z-]* ) $',
                     re.X)


Config = collections.namedtuple('Config', [
    'basedir',
    'baseurl',
    'branches_file',
    'noop',
    'series',
    'space',
    'skip',
    'repo_auth',
])


class Element(object):
    def __init__(self, name, type, parent_dir, fname, exists):
        self.name = name
        self.type = type
        self.parent_dir = parent_dir
        self.fname = fname
        self.exists = exists


StackConfig = collections.namedtuple('StackConfig', [
    'compute_charm',
    'storage_charm',

    'cinder_bare',
    'cinder_lxd',
    'cinder_machines',
    'cinder_targets',

    'nova_machines',
    'nova_targets',

    'all_machines',
    'all_targets',
])


def sp_msg(s):
    print(s)


def sp_chdir(cfg, dirname, do_chdir=False):
    if cfg.noop:
        sp_msg("# chdir -- '{dirname}'".format(dirname=dirname))
        if not do_chdir:
            return

    os.chdir(dirname)


def sp_mkdir(cfg, dirname):
    if cfg.noop:
        sp_msg("# mkdir -- '{dirname}'".format(dirname=dirname))
        return

    os.mkdir(dirname)


def sp_makedirs(cfg, dirname, mode=0o777, exist_ok=False):
    if cfg.noop:
        sp_msg("# makedirs '{dirname}' mode {mode:04o} exist_ok {exist_ok}"
               .format(dirname=dirname, mode=mode, exist_ok=exist_ok))
        return

    # *Sigh* Python 2 does not have exist_ok, does it now...
    if exist_ok and os.path.isdir(dirname):
        return
    os.makedirs(dirname, mode=mode)


def sp_run(cfg, command):
    if cfg.noop:
        sp_msg("# {command}".format(command=' '.join(command)))
        return

    subprocess.check_call(command)


def check_repository(cfg, url):
    comp = requests.utils.urlparse(url)
    if comp.scheme in ('http', 'https'):
        if cfg.noop:
            sp_msg('(would send an HTTP request to {url})'.format(url=url))
        else:
            return requests.request('GET', url).ok
    elif comp.scheme in ('', 'file'):
        return os.path.isdir(comp.path)
    else:
        # Leave it for the actual "git clone" to figure out
        # whether this exists.
        return True


def checkout_repository(cfg, name, branches):
    url = '{base}/{name}.git'.format(base=cfg.baseurl, name=name)
    try:
        if not check_repository(cfg, url):
            exit('The {name} StorPool repository does not seem to '
                 'exist at {url}'.format(name=name, url=url))
    except Exception as e:
        exit('Could not check for the existence of the {name} '
             'StorPool repository at {url}: {e}'
             .format(name=name, url=url, e=e))
    branch = branches.get(name, 'master')
    sp_msg('Checking out {url} branch {branch}'.format(url=url, branch=branch))
    try:
        sp_run(cfg, ['git', 'clone', '-b', branch, '--', url])
    except Exception:
        exit('Could not check out the {name} module'.format(name=name))


def is_file_not_found(e):
    try:
        return isinstance(e, FileNotFoundError)
    except NameError:
        return (isinstance(e, IOError) or isinstance(e, OSError)) and \
            e.errno == os.errno.ENOENT


def parse_layers(cfg, name, to_process, layers_required):
    if cfg.noop:
        sp_msg('(would examine the "layer.yaml" file and '
               'process layers and interfaces recursively)')
        return []

    try:
        with open('layer.yaml', mode='r') as f:
            contents = yaml.load(f)
    except Exception as e:
        if is_file_not_found(e) and not layers_required:
            return
        exit('Could not load the layer.yaml file from {name}: {e}'
             .format(name=name, e=e))

    for elem in contents['includes']:
        if elem.find('storpool') == -1 and elem != 'interface:cinder-backend':
            continue
        m = re_elem.match(elem)
        if m is None:
            exit('Invalid value "{elem}" in the {name} "includes" directive!'
                 .format(name=name, elem=elem))
        (e_type, e_name) = (m.groupdict()['type'], m.groupdict()['name'])

        parent_dir = '../{t}s'.format(t=e_type)
        fname = '{t}-{n}'.format(t=e_type, n=e_name)
        dname = '{parent}/{fname}'.format(parent=parent_dir, fname=fname)
        exists = os.path.exists(dname)
        if exists and not os.path.isdir(dname):
            exit('Something named {dname} exists and it is not a directory!'
                 .format(dname=dname))
        to_process.append(Element(
            name=e_name,
            type=e_type,
            parent_dir=parent_dir,
            fname=fname,
            exists=exists,
        ))


def checkout_element(cfg, name, branches, to_process, layers_required=False):
    checkout_repository(cfg, name, branches)
    sp_chdir(cfg, name)
    parse_layers(cfg, name, to_process, layers_required)
    sp_chdir(cfg, '../../charms')


def test_element(cfg):
    if os.path.isfile('tox.ini'):
        sp_msg('- running pep8/flake8 through tox')
        sp_run(cfg, ['tox', '-e', 'pep8'])
        sp_msg('- running all the tox tests')
        sp_run(cfg, ['tox', '-e', 'ALL'])
        # Sigh... the build gets confused.  A lot.
        sp_msg('- removing the .tox/ directory')
        sp_run(cfg, ['rm', '-rf', '.tox/'])
    else:
        sp_msg('- no tox.ini file, running some tests by ourselves')
        sp_msg('- running flake8')
        sp_run(cfg, ['flake8', '.'])
        sp_msg('- running pep8')
        sp_run(cfg, ['pep8', '.'])


def test_elements(cfg, paths):
    for path in paths:
        print('\n===== Testing {path}\n'.format(path=path))
        sp_chdir(cfg, '../' + path)
        test_element(cfg)
        sp_chdir(cfg, '../')


def sp_recurse(cfg, process_charm, process_element):
    sp_chdir(cfg, 'charms')

    to_process = []
    for name in charm_names:
        process_charm(name, to_process)

    processed = {}
    while True:
        if not to_process:
            sp_msg('No more layers or interfaces to process')
            break
        processing = six.itervalues({
            elem.fname: elem for elem in to_process
            if elem.fname not in processed and not elem.exists
        })
        to_process = []
        for elem in processing:
            sp_chdir(cfg, elem.parent_dir)
            process_element(cfg, elem, to_process)
            processed[elem.fname] = elem


def cmd_checkout(cfg):
    try:
        sp_chdir(cfg, cfg.basedir)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'
                 .format(d=cfg.basedir))
        raise

    if cfg.branches_file is not None:
        fn = cfg.branches_file
        sp_msg('Loading branches information from {fn}'.format(fn=fn))
        try:
            contents = open(fn, mode='r').read()
        except Exception as e:
            exit('Could not load the branches file {fn}: {e}'
                 .format(fn=fn, e=e))
        try:
            data = yaml.load(contents)
        except Exception as e:
            exit('Could not parse the branches file {fn} as YAML: {e}'
                 .format(fn=fn, e=e))
        if not isinstance(data, dict) or 'branches' not in data or \
           not isinstance(data['branches'], dict) or \
           [val for val in data['branches'] if not isinstance(val, str)]:
            exit('Invalid format for the branches file {fn}'.format(fn=fn))
        branches = data['branches']
    else:
        branches = {}

    sp_msg('Recreating the {subdir}/ tree'.format(subdir=subdir))
    sp_run(cfg, ['rm', '-rf', '--', subdir])
    sp_mkdir(cfg, subdir)
    sp_chdir(cfg, subdir)
    for comp in ('layers', 'interfaces', 'charms'):
        sp_mkdir(cfg, comp)

    def process_charm(name, to_process):
        sp_msg('Checking out the {name} charm'.format(name=name))
        checkout_element(cfg, name, branches, to_process, layers_required=True)
        processed.append('charms/' + name)

    def process_element(cfg, elem, to_process):
        sp_msg('Checking out the {name} {type}'
               .format(name=elem.name, type=elem.type))
        checkout_element(cfg, elem.fname, branches, to_process)
        processed.append(elem.type + 's/' + elem.fname)

    processed = []
    sp_recurse(cfg,
               process_charm=process_charm,
               process_element=process_element)

    sp_msg('The StorPool charms were checked out into {basedir}/{subdir}'
           .format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def cmd_pull(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Updating the charms in the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'
                 .format(d=subdir_full))
        raise

    def process_element(cfg, elem, to_process):
        sp_msg('Updating the {name} {type}'
               .format(name=elem.name, type=elem.type))
        sp_chdir(cfg, elem.fname)
        sp_run(cfg, ['git', 'pull', '--ff-only'])
        parse_layers(cfg, elem.name, to_process, False)
        processed.append(elem.type + 's/' + elem.fname)
        sp_chdir(cfg, '../')

    def process_charm(name, to_process):
        elem = Element(
            name=name,
            type='charm',
            parent_dir='',
            fname=name,
            exists=True,
        )
        process_element(cfg, elem, to_process)

    processed = []
    sp_recurse(cfg,
               process_charm=process_charm,
               process_element=process_element)

    sp_msg('The StorPool charms were updated in {basedir}/{subdir}'
           .format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def cmd_test(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Running tox tests for the charms in the {d} directory'
           .format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'
                 .format(d=subdir_full))
        raise

    def process_element(cfg, elem, to_process):
        sp_msg('Examining the {name} {type}'
               .format(name=elem.name, type=elem.type))
        sp_chdir(cfg, elem.fname)
        parse_layers(cfg, elem.name, to_process, False)
        processed.append(elem.type + 's/' + elem.fname)
        sp_chdir(cfg, '../')

    def process_charm(name, to_process):
        elem = Element(
            name=name,
            type='charm',
            parent_dir='',
            fname=name,
            exists=True,
        )
        process_element(cfg, elem, to_process)

    processed = []
    sp_recurse(cfg,
               process_charm=process_charm,
               process_element=process_element)

    sp_msg('Running the tox tests for {count} elements'
           .format(count=len(processed)))
    test_elements(cfg, sorted(processed))

    sp_msg('The StorPool charms were tested in {basedir}/{subdir}'
           .format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def charm_build_dir(basedir, name, series):
    return '{base}/built/{series}/{name}'.format(base=basedir,
                                                 series=series,
                                                 name=name)


def charm_deploy_dir(basedir, name, series):
    return '{build}/{series}/{name}' \
        .format(build=charm_build_dir(basedir, name, series),
                series=series,
                name=name)


def cmd_build(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Building the charms in the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full, do_chdir=True)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'
                 .format(d=subdir_full))
        raise
    basedir = os.getcwd()

    def process_charm(name, to_process):
        sp_msg('Building the {name} charm'.format(name=name))
        sp_chdir(cfg, name)
        short_name = name.replace('charm-', '')
        build_dir = charm_build_dir(basedir, short_name, cfg.series)
        sp_msg('- recreating the build directory')
        sp_run(cfg, ['rm', '-rf', '--', build_dir])
        sp_makedirs(cfg, build_dir, mode=0o755)
        sp_msg('- building the charm')
        sp_run(cfg, [
            'env',
            'LAYER_PATH={basedir}/layers'.format(basedir=basedir),
            'INTERFACE_PATH={basedir}/interfaces'.format(basedir=basedir),
            'charm', 'build', '-s', cfg.series, '-n', short_name,
            '-o', build_dir
        ])
        sp_chdir(cfg, '../')

    sp_recurse(cfg, process_charm=process_charm, process_element=None)
    sp_msg('The StorPool charms were built in {basedir}/{subdir}'
           .format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def find_charm(apps, names):
    charms_list = [elem for elem in six.iteritems(apps)
                   if elem[1]['charm-name'] in names]
    if len(charms_list) == 0:
        exit('Could not find a {names} charm deployed under any name'
             .format(names=' or '.join(names)))
    elif len(charms_list) > 1:
        exit('More than one {first_name} application is not supported'
             .format(first_name=names[0]))
    return charms_list[0][0]


def get_stack_config(cfg, status):
    """
    Examine a Juju cluster to find the Cinder and Nova nodes to deploy to.
    """
    compute_charm = find_charm(status['applications'],
                               ('nova-compute', 'nova-compute-kvm'))
    nova_machines = sorted([
        unit['machine'] for unit in six.itervalues(
            status['applications'][compute_charm]['units'])
    ])
    bad_nova_machines = [mach for mach in nova_machines if '/' in mach]
    if bad_nova_machines:
        exit('Nova deployed in a container or VM ({machines}) is not supported'
             .format(machines=','.join(bad_nova_machines)))
    nova_targets = set(nova_machines)

    storage_charm = find_charm(status['applications'], ('cinder'))
    cinder_machines = sorted([
        unit['machine'] for unit in six.itervalues(
            status['applications'][storage_charm]['units'])
    ])
    cinder_lxd = []
    cinder_bare = []
    for machine in cinder_machines:
        if '/lxd/' not in machine:
            cinder_bare.append(machine)
        else:
            cinder_lxd.append(machine)
    if cinder_bare:
        if cinder_lxd:
            exit('Cinder deployed both in containers ({lxd}) and '
                 'on bare metal ({bare}) is not supported'
                 .format(bare=', '.join(cinder_bare),
                         lxd=', '.join(cinder_lxd)))
        else:
            cinder_targets = set(cinder_bare)
    else:
        if not cinder_lxd:
            exit('Could not find the "{cinder}" charm deployed on '
                 'any Juju nodes'.format(cinder=storage_charm))
        cinder_targets = set(lxd.split('/', 1)[0] for lxd in cinder_lxd)
        cinder_machines = sorted(cinder_targets)

    if nova_targets.intersection(cinder_targets):
        cinder_machines = list(cinder_targets.difference(nova_targets))

    all_machines = sorted(set(cinder_bare +
                              cinder_lxd +
                              list(cinder_targets) +
                              list(nova_targets)))
    all_targets = cinder_targets.union(nova_targets)

    return StackConfig(
        compute_charm=compute_charm,
        storage_charm=storage_charm,

        cinder_lxd=cinder_lxd,
        cinder_bare=cinder_bare,
        cinder_machines=cinder_machines,
        cinder_targets=cinder_targets,

        nova_machines=nova_machines,
        nova_targets=nova_targets,

        all_machines=all_machines,
        all_targets=all_targets,
    )


def get_juju_status():
    status_j = subprocess.check_output(['juju', 'status', '--format=json'])
    return json.loads(status_j.decode())


def cmd_deploy(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Deplying the charms from the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full, do_chdir=True)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'
                 .format(d=subdir_full))
        raise
    basedir = os.getcwd()

    short_names = [name.replace('charm-', '') for name in charm_names]

    sp_msg('Obtaining the current Juju status')
    status = get_juju_status()
    found = [name for name in short_names if name in status['applications']]
    if found:
        exit('Found some StorPool charms already installed: {found}'
             .format(found=', '.join(found)))

    st = get_stack_config(cfg, status)

    sp_msg('Deploying the storpool-block charm')
    sp_run(cfg, [
        'juju', 'deploy', '--',
        charm_deploy_dir(basedir, 'storpool-block', cfg.series)
    ])

    sp_msg('Linking the storpool-block charm with the {nova} charm'
           .format(nova=st.compute_charm))
    sp_run(cfg, [
        'juju', 'add-relation',
        '{nova}:juju-info'.format(nova=st.compute_charm),
        'storpool-block:juju-info'
    ])

    if st.cinder_lxd:
        if st.cinder_machines:
            sp_msg('Deploying the storpool-candleholder charm to {machines}'
                   .format(machines=', '.join(st.cinder_machines)))
            sp_run(cfg, [
                'juju', 'deploy', '-n', str(len(st.cinder_machines)),
                '--to', ','.join(st.cinder_machines), '--',
                charm_deploy_dir(basedir, 'storpool-candleholder',
                                 cfg.series)
            ])

            sp_msg('Linking the storpool-candleholder charm with '
                   'the storpool-block charm')
            sp_run(cfg, [
                'juju', 'add-relation',
                'storpool-candleholder:juju-info',
                'storpool-block:juju-info'
            ])
        else:
            sp_msg('Apparently Cinder and Nova are on the same machines; '
                   'skipping the storpool-candleholder deployment')
    else:
        sp_msg('Linking the storpool-block charm with the {cinder} charm'
               .format(cinder=st.storage_charm))
        sp_run(cfg, [
            'juju', 'add-relation',
            '{cinder}:juju-info'.format(cinder=st.storage_charm),
            'storpool-block:juju-info'
        ])

    sp_msg('Deploying the cinder-storpool charm')
    sp_run(cfg, [
        'juju', 'deploy', '--',
        charm_deploy_dir(basedir, 'cinder-storpool', cfg.series)
    ])

    sp_msg('Linking the cinder-storpool charm with the {cinder} charm'
           .format(cinder=st.storage_charm))
    sp_run(cfg, [
        'juju', 'add-relation',
        '{cinder}:storage-backend'.format(cinder=st.storage_charm),
        'cinder-storpool:storage-backend'
    ])

    sp_msg('Linking the cinder-storpool charm with the storpool-block charm')
    sp_run(cfg, [
        'juju', 'add-relation',
        'storpool-block:storpool-presence',
        'cinder-storpool:storpool-presence'
    ])

    sp_msg('The StorPool charms were deployed from {basedir}/{subdir}'
           .format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def cmd_undeploy(cfg):
    short_names = [name.replace('charm-', '') for name in charm_names]

    sp_msg('Obtaining the current Juju status')
    status = get_juju_status()
    found = [name for name in short_names if name in status['applications']]
    if not found:
        exit('No StorPool charms are installed')
    else:
        sp_msg('About to remove {count} StorPool charms'
               .format(count=len(found)))

    for name in found:
        sp_msg('Removing the {name} Juju application'.format(name=name))
        sp_run(cfg, ['juju', 'remove-application', '--', name])

    sp_msg('Removed {count} StorPool charms'.format(count=len(found)))
    sp_msg('')


def cmd_upgrade(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Deplying the charms from the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full, do_chdir=True)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'
                 .format(d=subdir_full))
        raise
    basedir = os.getcwd()

    short_names = [name.replace('charm-', '') for name in charm_names]

    sp_msg('Obtaining the current Juju status')
    status = get_juju_status()
    found = [name for name in short_names if name in status['applications']]
    if not found:
        exit('No StorPool charms are installed')
    else:
        sp_msg('About to upgrade {count} StorPool charms'
               .format(count=len(found)))

    for name in found:
        sp_msg('Upgrading the {name} Juju application'.format(name=name))
        sp_run(cfg, [
            'juju', 'upgrade-charm',
            '--path', charm_deploy_dir(basedir, name, cfg.series), '--',
            name
        ])

    sp_msg('Upgraded {count} StorPool charms'.format(count=len(found)))
    sp_msg('')


def juju_ssh_single_line(cmd):
    output = subprocess.check_output(cmd).decode()
    lines = output.split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped:
            return stripped
    return ''


def get_storpool_config(cfg, status=None, stack=None):
    if not cfg.space:
        exit('No StorPool space (-S) specified')

    if status is None:
        status = get_juju_status()

    if stack is None:
        stack = get_stack_config(cfg, status)

    res = """
# Autogenerated StorPool test configuration

SP_CLUSTER_NAME=Juju charms test cluster
SP_CLUSTER_ID=a.a

SP_EXPECTED_NODES=3
SP_NODE_NON_VOTING=1
"""

    def correct_space(item):
        return item[1].get('space', None) == cfg.space

    for (oid, tgt) in enumerate(sorted(stack.all_targets)):
        name = juju_ssh_single_line(['juju', 'ssh', tgt, 'hostname'])
        mach = status['machines'][tgt]
        ifaces = [iface[0]
                  for iface in six.iteritems(mach['network-interfaces'])
                  if correct_space(iface)]
        if not ifaces:
            exit('Could not find any "{sp}" interfaces on {name} ({tgt}, {a})'
                 .format(sp=cfg.space, name=name, tgt=tgt, a=mach['dns-name']))
        res += """
[{name}]
SP_OURID={oid}
SP_IFACE={ifaces}
""".format(name=name, oid=oid + 40, ifaces=','.join(ifaces))

    return res


def cmd_generate_config(cfg):
    print(get_storpool_config(cfg))


def get_charm_config(cfg, stack, conf, bypass):
    ch = {
        'storpool-block': {
            'handle_lxc': bool(stack.cinder_lxd),
            'storpool_version': '16.02.165.c2e3456-1ubuntu1',
            'storpool_openstack_version': '1.3.0-1~1ubuntu1',
            'storpool_repo_url':
            'http://{auth}@repo.storpool.com/storpool-maas/'
            .format(auth=cfg.repo_auth),
            'storpool_conf': conf,
        },
        'cinder-storpool': {
            'storpool_template': 'hybrid-r3',
        },
    }

    if bypass:
        ch['storpool-block']['bypassed_checks'] = ','.join(sorted(bypass))
        ch['cinder-storpool']['bypassed_checks'] = ','.join(sorted(bypass))

    return yaml.dump(ch)


def cmd_generate_charm_config(cfg):
    if cfg.repo_auth is None:
        exit('No repository username:password (-A) specified')
    status = get_juju_status()
    stack = get_stack_config(cfg, status)
    conf = get_storpool_config(cfg, status=status)
    charmconf = get_charm_config(cfg, stack, conf, [])
    print(charmconf)


def deploy_wait(idx):
    reached = False
    max_itr = 60
    for itr in range(max_itr):
        sp_msg('- iteration {itr} of {max_itr}'
               .format(itr=itr + 1, max_itr=max_itr))
        sp_msg('  - obtaining the Juju status')
        cstatus = get_juju_status()
        sp_msg('  - comparing the status of the charms')
        pending = False
        for fname in charm_names:
            name = fname.replace('charm-', '')
            expected = charm_data[fname]['status'][idx]

            d = cstatus['applications'].get(name, None)
            if d is None:
                exit('The {name} charm is not there'.format(name=name))
            stati = [d['application-status']]
            if 'units' in d:
                stati.extend([unit['workload-status']
                              for unit in six.itervalues(d['units'])])

            charm_pending = False
            for sta in stati:
                msg = sta.get('message', '(no message)')
                if sta['current'] == 'error':
                    exit('The {name} charm is in the "error" state: {msg}'
                         .format(name=name, msg=msg))
                elif msg != expected and not charm_pending:
                    sp_msg('    - "{msg}" instead of "{exp}" for {name}'
                           .format(msg=msg, exp=expected, name=name))
                    charm_pending = True
                    pending = True

        if not pending:
            sp_msg('All the charms reached their expected status!')
            reached = True
            break
        sp_msg('  - apparently not yet, waiting')
        time.sleep(5)

    if not reached:
        exit('Some charms did not reach their expected status')


def undeploy_wait():
    reached = False
    for itr in range(60):
        sp_msg('- iteration {itr} of 60'.format(itr=itr + 1))
        sp_msg('  - obtaining the Juju status')
        cstatus = get_juju_status()
        sp_msg('  - examining the status of the charms')
        pending = False
        for fname in charm_names:
            name = fname.replace('charm-', '')
            d = cstatus['applications'].get(name, None)
            if d is None:
                continue
            stati = [d['application-status']]
            if 'units' in d:
                stati.extend([unit['workload-status']
                              for unit in six.itervalues(d['units'])])

            charm_pending = False
            for sta in stati:
                msg = sta.get('message', '(no message)')
                if sta['current'] == 'error':
                    exit('The {name} charm is in the "error" state: {msg}'
                         .format(name=name, msg=msg))
                elif not charm_pending:
                    sp_msg('    - {name} still there'.format(name=name))
                    charm_pending = True
                    pending = True

        if not pending:
            sp_msg('All the charms are gone!')
            reached = True
            break
        sp_msg('  - apparently not yet, waiting')
        time.sleep(5)

    if not reached:
        exit('Some charms could not be removed')


def check_systemd_units(stack, expected):
    sp_msg('Checking for the StorPool service unit files')
    services = ('storpool_beacon.service', 'storpool_block.service')
    for mach in sorted(stack.all_targets):
        output = subprocess.check_output([
            'juju', 'ssh', mach,
            'systemctl', '--no-pager', 'list-unit-files',
        ]).decode()
        found = set()
        for line in output.split('\n'):
            line = line.strip()
            words = line.split()
            if words and words[0] in services:
                if expected:
                    if 'enabled' not in words[1]:
                        exit('The {svc} service is not enabled on machine '
                             '{mach}: {line}'.format(svc=words[0],
                                                     mach=mach,
                                                     line=line))
                    else:
                        found.add(words[0])
                else:
                    if 'masked' not in words[1]:
                        exit('The {svc} service is not masked on machine '
                             '{mach}: {line}'.format(svc=words[0],
                                                     mach=mach,
                                                     line=line))
        if expected and len(found) != len(services):
            missing = ' '.join(sorted(set(services).difference(found)))
            exit('Services not found on machine {mach}: {missing}'
                 .format(mach=mach, missing=missing))


def cmd_deploy_test(cfg):
    if cfg.repo_auth is None:
        exit('No repository username:password (-A) specified')

    valid_skip_stages = (
        'assert-not-deployed',
        'build',
        'first-deploy',
        'first-deploy-wait',
        'first-undeploy',
        'first-undeploy-wait',
        'second-deploy',
        'config-block',
        'wait-block',
        'check-block',
        'config-cinder',
        'wait-cinder',
        'check-cinder',
        'second-undeploy',
        'second-undeploy-wait',
    )
    if cfg.skip:
        skip_stages = cfg.skip.split(',')
        invalid_skip_stages = [stage for stage in skip_stages
                               if stage not in valid_skip_stages]
        if invalid_skip_stages:
            exit('Invalid skip stages "{invalid}" specified; should be one or '
                 'more of {valid}'
                 .format(invalid=','.join(invalid_skip_stages),
                         valid=','.join(valid_skip_stages)))
        skip_stages = set(skip_stages)
    else:
        skip_stages = set()

    basedir = os.getcwd()

    sp_msg('Get the current Juju status')
    status = get_juju_status()
    if 'assert-not-deployed' not in skip_stages:
        found = [name for name in status['applications'].keys()
                 if 'storpool' in name]
        if found:
            exit('Please remove any StorPool-related charms first; '
                 'found {found}'.format(found=found))

    sp_msg('Examine the current Juju status for Cinder and Nova')
    stack = get_stack_config(cfg, status)

    if 'assert-not-deployed' not in skip_stages:
        check_systemd_units(stack, False)

    sp_msg('Check if any checks need to be bypassed')
    bypass = set(['use_cgroups'])
    for name in stack.all_machines:
        sp_msg('- checking machine {name}'.format(name=name))

        sp_msg('  - checking for the number of CPUs')
        first_line = juju_ssh_single_line([
            'juju', 'ssh', name,
            'egrep', '-ce', '^processor[[:space:]]', '/proc/cpuinfo',
        ])
        try:
            cnt = int(first_line)
        except ValueError:
            exit('Unexpected output from the processors count check for '
                 'machine {name}:\n{line}'.format(name=name, line=first_line))
        if cnt < 4:
            sp_msg('    - bypassing the CPU count check')
            bypass.add('very_few_cpus')

        sp_msg('  - checking for the available memory')
        first_line = juju_ssh_single_line([
            'juju', 'ssh', name,
            'head', '-n1', '/proc/meminfo',
        ])
        words = first_line.split()
        if len(words) != 3:
            exit('Unexpected output from the /proc/meminfo check for '
                 'machine {name}:\n{line}'.format(name=name, line=first_line))
        elif words[2] == 'kB':
            sp_msg('    - forcing a low-memory calculation')
            bypass.add('very_little_memory')

    sp_msg('Bypassing checks: {b}'.format(b=','.join(sorted(bypass))))

    sp_msg('Generate a sample StorPool config')
    conf = get_storpool_config(cfg, status=status, stack=stack)
    sp_msg('Generated a config file:\n{conf}'.format(conf=conf))

    sp_msg('Generate a full StorPool charms configuration')
    charmconf = get_charm_config(cfg, stack, conf, bypass)
    sp_msg('Generated charms configuration:\n{conf}'.format(conf=charmconf))

    def configure(charm):
        sp_msg('Now configuring {charm}'.format(charm=charm))
        with tempfile.NamedTemporaryFile(dir='/tmp',
                                         mode='w+t',
                                         delete=True) as tempf:
            print(charmconf, file=tempf, end='')
            tempf.flush()
            subprocess.check_call([
                'juju', 'config', '--file', tempf.name, charm,
            ])

    if 'build' not in skip_stages:
        sp_msg('Now running a build')
        cmd_build(cfg)
        os.chdir(basedir)

    if 'first-deploy' not in skip_stages:
        sp_msg('Now doing the initial deployment')
        cmd_deploy(cfg)
        os.chdir(basedir)

    if 'first-deploy-wait' not in skip_stages:
        sp_msg('Now waiting until the charms reach their first stage')
        deploy_wait(0)
        check_systemd_units(stack, False)

    if 'first-undeploy' not in skip_stages:
        sp_msg('Removing the applications')
        cmd_undeploy(cfg)
        os.chdir(basedir)

    if 'first-undeploy-wait' not in skip_stages:
        sp_msg('Waiting for the applications to disappear')
        undeploy_wait()
        check_systemd_units(stack, False)

    if 'second-deploy' not in skip_stages:
        sp_msg('Now deploying the charms again')
        cmd_deploy(cfg)
        os.chdir(basedir)

    if 'config-block' not in skip_stages:
        configure('storpool-block')

    if 'wait-block' not in skip_stages:
        deploy_wait(1)
        check_systemd_units(stack, True)

    if 'check-block' not in skip_stages:
        sp_msg('Verifying `storpool_showconf -ne SP_OURID`')
        for (oid, mach) in enumerate(sorted(stack.all_targets)):
            line = juju_ssh_single_line([
                'juju', 'ssh', mach,
                'storpool_showconf', '-ne', 'SP_OURID',
            ])
            if not line:
                exit('Could not run storpool_showconf on machine {mach}'
                     .format(mach=mach))
            bad = False
            try:
                moid = int(line)
                if moid != oid + 40:
                    bad = True
            except ValueError:
                bad = True
            if bad:
                exit('Unexpected output from `storpool_showconf -ne '
                     'SP_OURID` on machine {mach}: {line} (expected: {exp})'
                     .format(mach=mach, line=line, exp=oid + 40))

    if 'config-cinder' not in skip_stages:
        configure('cinder-storpool')

    if 'wait-cinder' not in skip_stages:
        deploy_wait(2)
        check_systemd_units(stack, True)

    if 'check-cinder' not in skip_stages:
        # Let's give Cinder a bit of time to write out the config file
        sp_msg('Giving Cinder some time to settle')
        time.sleep(15)
        sp_msg('Checking for cinder-storpool in /etc/cinder/cinder.conf')
        for mach in stack.cinder_lxd + stack.cinder_bare:
            line = juju_ssh_single_line([
                'juju', 'ssh', mach,
                'sudo', 'fgrep', 'cinder-storpool', '/etc/cinder/cinder.conf',
            ])
            if not line:
                exit('No cinder-storpool in /etc/cinder/cinder.conf on '
                     'machine {mach}'.format(mach=mach))

    if 'second-undeploy' not in skip_stages:
        sp_msg('Removing the applications')
        cmd_undeploy(cfg)
        os.chdir(basedir)

    if 'second-undeploy-wait' not in skip_stages:
        sp_msg('Waiting for the applications to disappear')
        undeploy_wait()
        check_systemd_units(stack, False)


COMMANDS = {
    'build': cmd_build,
    'deploy': cmd_deploy,
    'checkout': cmd_checkout,
    'pull': cmd_pull,
    'undeploy': cmd_undeploy,
    'upgrade': cmd_upgrade,
    'generate-config': cmd_generate_config,
    'generate-charm-config': cmd_generate_charm_config,
    'deploy-test': cmd_deploy_test,
    'test': cmd_test,
}


def main():
    parser = argparse.ArgumentParser(
        prog='storpool-charms',
        usage='''
        storpool-charms [-N] [-d basedir] [-s series] deploy
        storpool-charms [-N] [-d basedir] [-s series] upgrade
        storpool-charms [-N] [-d basedir] undeploy

        storpool-charms [-N] -S storpool-space generate-config
        storpool-charms [-N] -S storpool-space -A repo_auth generate-charm-config
        storpool-charms [-N] -S storpool-space -A repo_auth deploy-test

        storpool-charms [-N] [-B branches-file] [-d basedir] checkout
        storpool-charms [-N] [-d basedir] pull
        storpool-charms [-N] [-d basedir] test
        storpool-charms [-N] [-d basedir] [-s series] build

    The "-A repo_auth" option accepts a "repo_username:repo_password" parameter.

    A {subdir} directory will be created in the specified base directory.
    For the "checkout" and "pull" commands, specifying "-X tox" will not run
    the automated tests immediately after everything has been updated.'''
        .format(subdir=subdir),
    )
    parser.add_argument('-d', '--basedir', default='.',
                        help='specify the base directory for the charms tree')
    parser.add_argument('-N', '--noop', action='store_true',
                        help='no-operation mode, display what would be done')
    parser.add_argument('-s', '--series', default='xenial',
                        help='specify the name of the series to build for')
    parser.add_argument('-S', '--space',
                        help='specify the name of the StorPool network space')
    parser.add_argument('-U', '--baseurl', default=baseurl,
                        help='specify the base URL for the StorPool Git '
                        'repositories')
    parser.add_argument('-X', '--skip',
                        help='specify stages to skip during the deploy test')
    parser.add_argument('-A', '--repo-auth',
                        help='specify the StorPool repository authentication data')
    parser.add_argument('-B', '--branches-file',
                        help='specify the YAML file listing the branches to '
                             'check out')
    parser.add_argument('command', choices=sorted(COMMANDS.keys()))

    args = parser.parse_args()
    cfg = Config(
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
