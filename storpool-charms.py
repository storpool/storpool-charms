#!/usr/bin/python

from __future__ import print_function

import argparse
import json
import os
import re
import requests
import subprocess
import yaml
import six

baseurl='https://github.com/storpool'
subdir='storpool-charms'
charm_names=['charm-storpool-block', 'charm-cinder-storpool', 'charm-storpool-inventory']
charm_series='xenial'
re_elem = re.compile('(?P<type> (?: layer | interface ) ) : (?P<name> [a-z][a-z-]* ) $', re.X)


class Config(object):
    def __init__(self, basedir, baseurl, suffix, noop):
        self.basedir = basedir
        self.baseurl = baseurl
        self.suffix = suffix
        self.noop = noop


class Element(object):
    def __init__(self, name, type, parent_dir, fname, exists):
        self.name = name
        self.type = type
        self.parent_dir = parent_dir
        self.fname = fname
        self.exists = exists


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
        sp_msg("# makedirs '{dirname}' mode {mode:04o} exist_ok {exist_ok}".format(dirname=dirname, mode=mode, exist_ok=exist_ok))
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
        # Leave it for the actual "git clone" to figure out whether this exists.
        return True

def checkout_repository(cfg, name):
    url = '{base}/{name}.git'.format(base=cfg.baseurl, name=name)
    try:
        if not check_repository(cfg, url):
            exit('The {name} StorPool repository does not seem to exist at {url}'.format(name=name, url=url))
    except Exception as e:
        exit('Could not check for the existence of the {name} StorPool repository at {url}: {e}'.format(name=name, url=url, e=e))
    sp_msg('Checking out {url}'.format(url=url))
    try:
        sp_run(cfg, ['git', 'clone', '--', url]);
    except Exception:
        exit('Could not check out the {name} module'.format(name=name))


def is_file_not_found(e):
    try:
        return isinstance(e, FileNotFoundError)
    except NameError:
        return (isinstance(e, IOError) or isinstance(e, OSError)) and e.errno == os.errno.ENOENT


def parse_layers(cfg, to_process, layers_required):
    if cfg.noop:
        sp_msg('(would examine the "layer.yaml" file and process layers and interfaces recursively)')
        return []

    try:
        with open('layer.yaml', mode='r') as f:
            contents = yaml.load(f)
    except Exception as e:
        if is_file_not_found(e) and not layers_required:
            return
        exit('Could not load the layer.yaml file from {name}: {e}'.format(name=name, e=e))

    for elem in filter(lambda e: e.find('storpool') != -1, contents['includes']):
        m = re_elem.match(elem)
        if m is None:
            exit('Invalid value "{elem}" in the {name} "includes" directive!'.format(name=name, elem=elem))
        (e_type, e_name) = (m.groupdict()['type'], m.groupdict()['name'])

        parent_dir = '../{t}s'.format(t=e_type)
        fname = '{t}-{n}'.format(t=e_type, n=e_name)
        dname = '{parent}/{fname}'.format(parent=parent_dir, fname=fname)
        exists = os.path.exists(dname)
        if exists and not os.path.isdir(dname):
            exit('Something named {dname} exists and it is not a directory!'.format(dname=dname))
        to_process.append(Element(
            name=e_name,
            type=e_type,
            parent_dir=parent_dir,
            fname=fname,
            exists=exists,
        ))


def checkout_element(cfg, name, to_process, layers_required=False):
    checkout_repository(cfg, name)
    sp_chdir(cfg, name)
    sp_msg('- running flake8')
    sp_run(cfg, ['flake8', '.'])
    sp_msg('- running pep8')
    sp_run(cfg, ['pep8', '.'])
    parse_layers(cfg, to_process, layers_required)
    sp_chdir(cfg, '../../charms')

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
        processing = six.itervalues(dict(map(
            lambda e: (e.fname, e),
            filter(
                lambda e: e.fname not in processed and not e.exists,
                to_process)
        )))
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
            exit('The {d} directory does not seem to exist!'.format(d=cfg.basedir))
        raise

    sp_msg('Recreating the {subdir}/ tree'.format(subdir=subdir))
    sp_run(cfg, ['rm', '-rf', '--', subdir])
    sp_mkdir(cfg, subdir)
    sp_chdir(cfg, subdir)
    for comp in ('layers', 'interfaces', 'charms'):
        sp_mkdir(cfg, comp)
    
    def process_charm(name, to_process):
        sp_msg('Checking out the {name} charm'.format(name=name))
        checkout_element(cfg, name, to_process, layers_required=True)

    def process_element(cfg, elem, to_process):
        sp_msg('Checking out the {name} {type}'.format(name=elem.name, type=elem.type))
        checkout_element(cfg, elem.fname, to_process)

    sp_recurse(cfg, process_charm=process_charm, process_element=process_element)
    sp_msg('The StorPool charms were checked out into {basedir}/{subdir}'.format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def cmd_pull(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Updating the charms in the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'.format(d=subdir_full))
        raise

    def process_element(cfg, elem, to_process):
        sp_msg('Updating the {name} {type}'.format(name=elem.name, type=elem.type))
        sp_chdir(cfg, elem.fname)
        sp_run(cfg, ['git', 'pull', '--ff-only'])
        parse_layers(cfg, to_process, False)
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

    sp_recurse(cfg, process_charm=process_charm, process_element=process_element)
    sp_msg('The StorPool charms were updated in {basedir}/{subdir}'.format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def charm_build_dir(basedir, name):
    return '{base}/built/{series}/{name}'.format(base=basedir, series=charm_series, name=name)


def charm_deploy_dir(basedir, name):
    return '{build}/{series}/{name}'.format(build=charm_build_dir(basedir, name), series=charm_series, name=name)


def cmd_build(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Building the charms in the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full, do_chdir=True)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'.format(d=subdir_full))
        raise
    basedir = os.getcwd()

    def process_charm(name, to_process):
        sp_msg('Building the {name} charm'.format(name=name))
        sp_chdir(cfg, name)
        short_name = name.replace('charm-', '')
        build_dir = charm_build_dir(basedir, short_name)
        sp_msg('- recreating the build directory')
        sp_run(cfg, ['rm', '-rf', '--', build_dir])
        sp_makedirs(cfg, build_dir, mode=0o755)
        sp_msg('- building the charm')
        sp_run(cfg, [
            'env',
            'LAYER_PATH={basedir}/layers'.format(basedir=basedir),
            'INTERFACE_PATH={basedir}/interfaces'.format(basedir=basedir),
            'charm', 'build', '-s', charm_series, '-n', short_name, '-o', build_dir
        ])
        sp_chdir(cfg, '../')

    sp_recurse(cfg, process_charm=process_charm, process_element=None)
    sp_msg('The StorPool charms were deployed from {basedir}/{subdir}'.format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def find_charm(apps, names):
    charms_list = list(filter(lambda e: e[1]['charm-name'] in names, six.iteritems(apps)))
    if len(charms_list) == 0:
        exit('Could not find a {names} charm deployed under any name'.format(names=' or '.join(names)))
    elif len(charms_list) > 1:
        exit('More than one {first_name} application is not supported'.format(first_name=names[0]))
    return charms_list[0][0]


def cmd_deploy(cfg):
    subdir_full = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    sp_msg('Deplying the charms from the {d} directory'.format(d=subdir_full))
    try:
        sp_chdir(cfg, subdir_full, do_chdir=True)
    except Exception as e:
        if is_file_not_found(e):
            exit('The {d} directory does not seem to exist!'.format(d=subdir_full))
        raise
    basedir = os.getcwd()

    short_names = list(map(lambda s: s.replace('charm-', ''), charm_names))

    sp_msg('Obtaining the current Juju status')
    status_j = subprocess.check_output(['juju', 'status', '--format=json'])
    status = json.loads(status_j.decode())
    found = list(filter(lambda name: name in status['applications'], short_names))
    if found:
        exit('Found some StorPool charms already installed: {found}'.format(found=', '.join(found)))

    compute_charm = find_charm(status['applications'], ('nova-compute', 'nova-compute-kvm'))
    nova_machines = sorted(map(lambda e: e['machine'], six.itervalues(status['applications'][compute_charm]['units'])))
    bad_nova_machines = list(filter(lambda s: '/' in s, nova_machines))
    if bad_nova_machines:
        exit('Nova deployed in a container or VM ({machines}) is not supported'.format(machines=','.join(bad_nova_machines)))
    nova_targets = set(nova_machines)

    storage_charm = find_charm(status['applications'], ('cinder'))
    cinder_machines = sorted(map(lambda e: e['machine'], six.itervalues(status['applications'][storage_charm]['units'])))
    cinder_lxd = []
    cinder_bare = []
    for machine in cinder_machines:
        if '/lxd/' not in machine:
            cinder_bare.append(machine)
        else:
            cinder_lxd.append(machine)
    if cinder_bare:
        if cinder_lxd:
            exit('Cinder deployed both in containers ({lxd}) and on bare metal ({bare}) is not supported'.format(bare=', '.join(cinder_bare), lxd=', '.join(cinder_lxd)))
        else:
            cinder_targets = set(cinder_bare)
    else:
        if not cinder_lxd:
            exit('Could not find the "{cinder}" charm deployed on any Juju nodes'.format(cinder=storage_charm))
        cinder_targets = set(map(lambda s: s.split('/', 1)[0], cinder_lxd))
    
    if nova_targets.intersection(cinder_targets):
        exit('Cinder and Nova deployed on the same machines ({same}) is not supported'.format(same=', '.join(sorted(nova_targets.intersection(cinder_targets)))))

    sp_msg('Deploying the storpool-block charm')
    sp_run(cfg, ['juju', 'deploy', '--', charm_deploy_dir(basedir, 'storpool-block')])

    sp_msg('Linking the storpool-block charm with the {nova} charm'.format(nova=compute_charm))
    sp_run(cfg, ['juju', 'add-relation', '{nova}:juju-info'.format(nova=compute_charm), 'storpool-block:juju-info'])

    if cinder_lxd:
        cinder_machines = sorted(cinder_targets)
        sp_msg('Deploying the storpool-inventory charm to {machines}'.format(machines=', '.join(cinder_machines)))
        sp_run(cfg, ['juju', 'deploy', '-n', str(len(cinder_machines)), '--to', ','.join(cinder_machines), '--', charm_deploy_dir(basedir, 'storpool-inventory')])

        sp_msg('Linking the storpool-inventory charm with the storpool-block charm')
        sp_run(cfg, ['juju', 'add-relation', 'storpool-inventory:juju-info', 'storpool-block:juju-info'])
    else:
        sp_msg('Linking the storpool-block charm with the {cinder} charm'.format(cinder=storage_charm))
        sp_run(cfg, ['juju', 'add-relation', '{cinder}:juju-info'.format(cinder=storage_charm), 'storpool-block:juju-info'])

    sp_msg('Deploying the cinder-storpool charm')
    sp_run(cfg, ['juju', 'deploy', '--', charm_deploy_dir(basedir, 'cinder-storpool')])

    sp_msg('Linking the cinder-storpool charm with the {cinder} charm'.format(cinder=storage_charm))
    sp_run(cfg, ['juju', 'add-relation', '{cinder}:storage-backend'.format(cinder=storage_charm), 'cinder-storpool:storage-backend'])

    sp_msg('Linking the cinder-storpool charm with the storpool-block charm')
    sp_run(cfg, ['juju', 'add-relation', 'storpool-block:storpool-presence', 'cinder-storpool:storpool-presence'])
        
    sp_msg('The StorPool charms were deployed from {basedir}/{subdir}'.format(basedir=cfg.basedir, subdir=subdir))
    sp_msg('')


def cmd_undeploy(cfg):
    short_names = list(map(lambda s: s.replace('charm-', ''), charm_names))

    sp_msg('Obtaining the current Juju status')
    status_j = subprocess.check_output(['juju', 'status', '--format=json'])
    status = json.loads(status_j.decode())
    found = list(filter(lambda name: name in status['applications'], short_names))
    if not found:
        exit('No StorPool charms are installed')
    else:
        sp_msg('About to remove {count} StorPool charms'.format(count=len(found)))

    for name in found:
        sp_msg('Removing the {name} Juju application'.format(name=name))
        sp_run(cfg, ['juju', 'remove-application', '--', name])

    sp_msg('Removed {count} StorPool charms'.format(count=len(found)))
    sp_msg('')


def cmd_dist(cfg):
    if cfg.suffix is None or cfg.suffix == '':
        exit('No distribution suffix (-s) specified')
    basedir = '{base}/{subdir}'.format(base=cfg.basedir, subdir=subdir)
    dist_name = 'storpool-charms-{series}-{suffix}'.format(series=charm_series, suffix=cfg.suffix)
    dist_path = '{base}/{name}'.format(base=cfg.basedir, name=dist_name)
    dist_tar_temp = '{name}.tar'.format(name=dist_name)
    dist_tarball = '{tar}.xz'.format(tar=dist_tar_temp)
    sp_msg('Creating {tarball} in {basedir}'.format(tarball=dist_tarball, basedir=cfg.basedir))

    sp_msg('Copying the charms tree {base}'.format(base=basedir))
    sp_run(cfg, ['rm', '-rf', '--', dist_path])
    sp_mkdir(cfg, dist_path)
    sp_run(cfg, [
        'cp', '-Rp', '--',
        basedir,
        '{dist}/{subdir}'.format(dist=dist_path, subdir=subdir),
    ])

    sp_msg('Copying the storpool-charms helper tools')
    for fname in subprocess.check_output(['git', 'ls-files']).decode().split('\n'):
        if fname == '':
            continue
        sp_run(cfg, ['cp', '-p', '--', fname, '{dist}/{fname}'.format(dist=dist_path, fname=fname)])

    vers = subprocess.check_output(['git', 'describe']).decode().split('\n', 1)[0]
    versions = {'storpool-charms': vers}

    sp_chdir(cfg, '{dist}/{subdir}'.format(dist=dist_path, subdir=subdir))
    if cfg.noop:
        sp_msg('(would gather the charm versions)')
    else:
        sp_msg('Gathering the charm versions')
        charm_subdirs = []
        for root, dirs, _ in os.walk('.'):
            comp = root.split('/')
            if len(comp) == 1:
                for extra in filter(lambda s: s not in ('charms', 'layers', 'interfaces'), dirs):
                    dirs.remove(extra)
            elif len(comp) == 3:
                (c_type, c_name) = comp[-2:]
                if c_name.startswith(c_type[:-1]):
                    path = '/'.join([c_type, c_name])
                    charm_subdirs.append(path)
                # Right, Python 2 doesn't have clear(), either.
                while dirs:
                    dirs.pop()

        for path in charm_subdirs:
            sp_chdir(cfg, path)
            name = path.split('/')[-1]
            vers = subprocess.check_output(['git', 'describe']).decode().split('\n', 1)[0]
            versions[name] = vers
            sp_chdir(cfg, '../..')

        with open('versions.txt', mode='w') as f:
            f.writelines(map(lambda e: '{name}\t{vers}\n'.format(name=e[0], vers=e[1]), sorted(six.iteritems(versions))))

    sp_msg('Creating the tarball')
    sp_chdir(cfg, '../..')
    sp_run(cfg, ['rm', '-f', '--', dist_tar_temp, dist_tarball])
    sp_run(cfg, ['tar', 'cf', dist_tar_temp, dist_name])
    sp_run(cfg, ['xz', '-9', '--', dist_tar_temp])
    sp_run(cfg, ['rm', '-rf', '--', dist_tar_temp, dist_name])

    sp_msg('Created {base}/{tarball}'.format(tarball=dist_tarball, base=cfg.basedir))
    sp_msg('')


parser = argparse.ArgumentParser(
    prog='storpool-charms',
    usage='''
    storpool-charms [-N] [-d basedir] deploy
    storpool-charms [-N] [-d basedir] undeploy

    storpool-charms [-N] [-d basedir] checkout
    storpool-charms [-N] [-d basedir] pull
    storpool-charms [-N] [-d basedir] build
    storpool-charms [-N] [-d basedir] dist

A {subdir} directory will be created in the specified base directory.'''.format(subdir=subdir),
)
parser.add_argument('-d', '--basedir', default='.', help='specify the base directory for the charms tree')
parser.add_argument('-N', '--noop', action='store_true', help='no-operation mode, display what would be done')
parser.add_argument('-s', '--suffix', help='specify the suffix for the distribution name')
parser.add_argument('-U', '--baseurl', default=baseurl, help='specify the base URL for the StorPool Git repositories')
parser.add_argument('command', choices=['build', 'checkout', 'deploy', 'dist', 'pull', 'undeploy'])

args = parser.parse_args()
cfg = Config(
    basedir = args.basedir,
    baseurl = args.baseurl,
    suffix = args.suffix,
    noop = args.noop,
)

commands = {
    'build': cmd_build,
    'deploy': cmd_deploy,
    'dist': cmd_dist,
    'checkout': cmd_checkout,
    'pull': cmd_pull,
    'undeploy': cmd_undeploy,
}
commands[args.command](cfg)
