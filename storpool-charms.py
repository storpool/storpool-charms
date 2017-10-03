#!/usr/bin/python

from __future__ import print_function

import argparse
import os
import re
import requests
import subprocess
import yaml
import six
import sys

base_url='https://github.com/storpool'
subdir='storpool-charms'
charm_names=['charm-storpool-block', 'charm-cinder-storpool', 'charm-storpool-inventory']
re_elem = re.compile('(?P<type> (?: layer | interface ) ) : (?P<name> [a-z][a-z-]* ) $', re.X)


class Config(object):
	def __init__(self, basedir, noop):
		self.basedir = basedir
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

def sp_chdir(cfg, dirname):
	if cfg.noop:
		sp_msg("# chdir -- '{dirname}'".format(dirname=dirname))
		return

	os.chdir(dirname)

def sp_mkdir(cfg, dirname):
	if cfg.noop:
		sp_msg("# mkdir -- '{dirname}'".format(dirname=dirname))
		return

	os.mkdir(dirname)

def sp_run(cfg, command):
	if cfg.noop:
		sp_msg("# {command}".format(command=' '.join(command)))
		return

	subprocess.check_call(command)

def checkout_repository(cfg, name):
	url = '{base}/{name}.git'.format(base=base_url, name=name)
	try:
		if not requests.request('GET', url).ok:
			exit('The {name} StorPool repository does not seem to exist on GitHub!'.format(name=name))
	except Exception as e:
		exit('Could not check for the existence of the {name} StorPool repository on GitHub: {e}'.format(name=name, e=e))
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
		sp_msg('(would examine the "layer.yaml" file and check out layers and interfaces recursively)')
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

	sp_msg('The StorPool charms were checked out into {basedir}/{subdir}'.format(basedir=cfg.basedir, subdir=subdir))
	sp_msg('')


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


parser = argparse.ArgumentParser(
	prog='storpool-charms',
	usage='''
	storpool-charms [-N] [-d basedir] checkout

A {subdir} directory will be created in the specified base directory.'''.format(subdir=subdir),
)
parser.add_argument('-d', '--basedir', default='.', help='specify the base directory for the charms tree')
parser.add_argument('-N', '--noop', action='store_true', help='no-operation mode, display what would be done')
parser.add_argument('command', choices=['checkout'])

args = parser.parse_args()
cfg = Config(basedir = args.basedir, noop = args.noop)

commands = {
	'checkout': cmd_checkout,
}
commands[args.command](cfg)
