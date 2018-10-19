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
Tests for the storpool.charms.manage.juju module.
"""


import re
import unittest

from typing import cast, Dict, List

import mock

from storpool.charms.manage import config as cconfig
from storpool.charms.manage import data as cdata
from storpool.charms.manage import juju as cjuju


_TYPING_USED = (cdata,)


JSON_CANDLEHOLDER = """
{
    "controller": {
        "timestamp": "now"
    },

    "applications": {
        "something": {
            "charm-name": "cinder",
            "series": "xenial",
            "units": {
                "cinder/0": {
                    "machine": "0/lxd/1"
                },

                "cinder/1": {
                    "machine": "2/lxd/3"
                }
            }
        },

        "something-else": {
            "charm-name": "nova-compute",
            "series": "bionic",
            "units": {
                "something-else/11": {
                    "machine": "1"
                },

                "something-else/20": {
                    "machine": "0"
                }
            }
        },

        "entirely-different": {
            "charm-name": "swift",
            "series": "xenial"
        }
    },

    "machines": {
        "0": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s11.lab",
            "ip-addresses": [
                "10.1.1.11",
                "10.1.2.11",
                "10.1.3.11"
            ],
            "instance-id": "kyapk6",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "series": "xenial",
            "containers": {
                "0/lxd/1": {
                    "juju-status": {
                        "current": "started",
                        "since": "today, but a bit later",
                        "version": "2.4-rc3"
                    },
                    "dns-name": "10.1.66.33",
                    "ip-addresses": [
                        "10.1.66.33"
                    ],
                    "instance-id": "juju-container-0-lxd-1",
                    "machine-status": {
                        "current": "running",
                        "message": "Container started",
                        "since": "today, but a bit later"
                    },
                    "series": "bionic",
                    "constraints": "spaces=storpool"
                }
            },
            "constraints": "spaces=mgmt,storpool"
        },

        "1": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s12.lab",
            "ip-addresses": [
                "10.1.1.12",
                "10.1.2.12",
                "10.1.3.12"
            ],
            "instance-id": "4p3nfh",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "series": "trusty",
            "containers": {
                "1/lxd/0": {
                    "juju-status": {
                        "current": "started",
                        "since": "today, but a bit later",
                        "version": "2.4-rc3"
                    },
                    "dns-name": "10.1.66.34",
                    "ip-addresses": [
                        "10.1.66.34"
                    ],
                    "instance-id": "juju-container-1-lxd-0",
                    "machine-status": {
                        "current": "running",
                        "message": "Container started",
                        "since": "today, but a bit later"
                    },
                    "series": "trusty",
                    "constraints": "spaces=storpool"
                }
            },
            "constraints": "storpool"
        },

        "2": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s13.lab",
            "ip-addresses": [
                "10.1.1.13",
                "10.1.2.13",
                "10.1.3.13"
            ],
            "instance-id": "76hmpk",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "series": "xenial",
            "containers": {
                "2/lxd/3": {
                    "juju-status": {
                        "current": "started",
                        "since": "today, but a bit later",
                        "version": "2.4-rc3"
                    },
                    "dns-name": "10.1.66.35",
                    "ip-addresses": [
                        "10.1.66.35"
                    ],
                    "instance-id": "juju-container-2-lxd-3",
                    "machine-status": {
                        "current": "running",
                        "message": "Container started",
                        "since": "today, but a bit later"
                    },
                    "series": "xenial",
                    "constraints": "spaces=storpool"
                }
            },
            "constraints": "storpool,mgmt"
        },

        "3": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s14.lab",
            "ip-addresses": [
                "10.1.1.14",
                "10.1.2.14",
                "10.1.3.14"
            ],
            "instance-id": "nyaphk",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "series": "xenial",
            "constraints": "another"
        }
    }
}
"""


JSON_REAL = """
{
    "controller": {
        "timestamp": "now"
    },

    "applications": {
        "something": {
            "charm-name": "cinder",
            "series": "xenial",
            "units": {
                "cinder/0": {
                    "machine": "0/lxd/1"
                },

                "cinder/1": {
                    "machine": "1/lxd/0"
                }
            }
        },

        "something-else": {
            "charm-name": "nova-compute",
            "series": "bionic",
            "units": {
                "something-else/11": {
                    "machine": "1"
                },

                "something-else/20": {
                    "machine": "0"
                }
            }
        },

        "entirely-different": {
            "charm-name": "swift",
            "series": "xenial"
        }
    },

    "machines": {
        "0": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s11.lab",
            "ip-addresses": [
                "10.1.1.11",
                "10.1.2.11",
                "10.1.3.11"
            ],
            "instance-id": "kyapk6",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "network-interfaces": {
                "eth0": {
                    "space": "mgmt"
                },
                "enp2s0": {
                    "space": "storpool"
                },
                "eth2": {
                }
            },
            "series": "xenial",
            "containers": {
                "0/lxd/1": {
                    "juju-status": {
                        "current": "started",
                        "since": "today, but a bit later",
                        "version": "2.4-rc3"
                    },
                    "dns-name": "10.1.66.33",
                    "ip-addresses": [
                        "10.1.66.33"
                    ],
                    "instance-id": "juju-container-0-lxd-1",
                    "machine-status": {
                        "current": "running",
                        "message": "Container started",
                        "since": "today, but a bit later"
                    },
                    "network-interfaces": {
                        "eth0": {
                            "space": "storpool"
                        }
                    },
                    "series": "bionic",
                    "constraints": "spaces=storpool"
                }
            },
            "constraints": "spaces=mgmt,storpool"
        },

        "1": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s12.lab",
            "ip-addresses": [
                "10.1.1.12",
                "10.1.2.12",
                "10.1.3.12"
            ],
            "instance-id": "4p3nfh",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "network-interfaces": {
                "eth0": {
                },
                "eth0.403": {
                    "space": "storpool"
                },
                "eth1": {
                },
                "eth2": {
                }
            },
            "series": "trusty",
            "containers": {
                "1/lxd/0": {
                    "juju-status": {
                        "current": "started",
                        "since": "today, but a bit later",
                        "version": "2.4-rc3"
                    },
                    "dns-name": "10.1.66.34",
                    "ip-addresses": [
                        "10.1.66.34"
                    ],
                    "instance-id": "juju-container-1-lxd-0",
                    "machine-status": {
                        "current": "running",
                        "message": "Container started",
                        "since": "today, but a bit later"
                    },
                    "network-interfaces": {
                        "eth0": {
                            "space": "storpool"
                        }
                    },
                    "series": "trusty",
                    "constraints": "spaces=storpool"
                }
            },
            "constraints": "storpool"
        },

        "2": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s13.lab",
            "ip-addresses": [
                "10.1.1.13",
                "10.1.2.13",
                "10.1.3.13"
            ],
            "instance-id": "76hmpk",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "network-interfaces": {
                "br-storpool": {
                    "space": "storpool"
                },
                "eth1": {
                },
                "eth2": {
                    "space": "mgmt"
                }
            },
            "series": "xenial",
            "containers": {
                "2/lxd/3": {
                    "juju-status": {
                        "current": "started",
                        "since": "today, but a bit later",
                        "version": "2.4-rc3"
                    },
                    "dns-name": "10.1.66.35",
                    "ip-addresses": [
                        "10.1.66.35"
                    ],
                    "instance-id": "juju-container-2-lxd-3",
                    "machine-status": {
                        "current": "running",
                        "message": "Container started",
                        "since": "today, but a bit later"
                    },
                    "series": "xenial",
                    "constraints": "spaces=storpool"
                }
            },
            "constraints": "storpool,mgmt"
        },

        "3": {
            "juju-status": {
                "current": "started",
                "since": "today",
                "version": "2.4-rc3"
            },
            "dns-name": "s14.lab",
            "ip-addresses": [
                "10.1.1.14",
                "10.1.2.14",
                "10.1.3.14"
            ],
            "instance-id": "nyaphk",
            "machine-status": {
                "current": "running",
                "message": "Deployed",
                "since": "earlier today"
            },
            "series": "xenial",
            "constraints": "another"
        }
    }
}
"""

CHARM_TYPES = {
    'something': 'storage',
    'something-else': 'compute',
}


class TestStatus(unittest.TestCase):
    """ Test the get_status() function. """

    @mock.patch('subprocess.check_output')
    def test_fail(self, check_output: mock.MagicMock) -> None:
        """ Test the get_status() function. """

        class WeirdError(Exception):
            """ Just something to raise... """

            def __init__(self, cmd: List[str]) -> None:
                """ Record what we raised. """
                super(WeirdError, self).__init__()
                self.cmd = cmd

        def error_out(cmd: List[str]) -> None:
            """ Raise an exception. """
            raise WeirdError(cmd)

        check_output.side_effect = error_out
        with self.assertRaises(cjuju.RunError) as err_r:
            cjuju.get_status()
        err_re = err_r.exception
        self.assertIsInstance(err_re.error, WeirdError)
        err_we = cast(WeirdError, err_re.error)
        self.assertEqual(err_we.cmd, ['juju', 'status', '--format=json'])

        check_output.side_effect = None
        check_output.return_value = ']:['.encode('UTF-8')
        with self.assertRaises(cjuju.DecodeError) as err_d:
            cjuju.get_status()
        err_de = err_d.exception
        self.assertIsInstance(err_de.error, ValueError)

    def do_test_real(self,
                     exp_apps: List[str],
                     exp_mach_type: Dict[str, List[str]],
                     exp_sp_chosen: Dict[str, str],
                     exp_sp_machines: Dict[str, List[str]]) -> None:
        """ Test with a real configuration. """
        res = cjuju.get_status()
        self.assertEqual(res['controller']['timestamp'], 'now')
        self.assertEqual(sorted(res['applications'].keys()), exp_apps)

        meta_apps = res['_meta']['applications']
        meta_mach = res['_meta']['machines']
        meta_sp = res['_meta']['sp']

        for name, app in res['applications'].items():
            self.assertEqual(app['_name'], name)
            self.assertIs(app, meta_apps['by_charm'][app['charm-name']][name])
            ctype = CHARM_TYPES.get(name, None)
            if ctype is not None:
                self.assertEqual(app['_type'], ctype)
                self.assertIs(app,
                              meta_apps['by_type'][CHARM_TYPES[name]][name])
            else:
                self.assertIsNone(app['_type'])
                self.assertEqual(name, 'entirely-different')

            for uname, unit in app.get('units', {}).items():
                self.assertEqual(unit['_name'], uname)
                self.assertIs(unit['_app'], app)

                # Bah, union types, am I right?
                umach = cast(cdata.Container, unit['_mach'])
                self.assertIs(umach, meta_mach['all'][umach['_mid']])
                self.assertIsInstance(umach['_units'], dict)

                if ctype is not None:
                    self.assertEqual(umach['_type'], ctype)
                    self.assertIn(umach['_mid'], meta_mach['by_type'][ctype])
                else:
                    self.assertIsNone(umach['_type'])
                self.assertIs(unit, umach['_units'][uname])

        self.assertEqual(sorted(meta_mach['by_type']['storage'].keys()),
                         exp_mach_type['storage'])
        self.assertEqual(sorted(meta_mach['by_type']['compute'].keys()),
                         exp_mach_type['compute'])

        m_re = re.compile(r'^(?: 0 | [1-9][0-9]* ) $', re.X)
        for mid, mach in meta_mach['all'].items():
            mtype = cast(cdata.Container, mach)['_mtype']
            if mtype == 'container':
                continue  # handled as part of its parent machine
            self.assertRegex(mid, m_re)
            mach_m = cast(cdata.Machine, mach)

            c_re = re.compile(r'^ ' + mid + r'/lxd/ ( 0 | [1-9][0-9]* ) $',
                              re.X)
            for cid, cont in mach_m.get('containers', {}).items():
                self.assertRegex(cid, c_re)
                self.assertIs(cont['_mach'], mach_m)

        self.assertEqual(meta_sp['chosen_charm'], exp_sp_chosen)
        self.assertEqual(meta_sp['machines'], exp_sp_machines)

    @mock.patch('subprocess.check_output')
    def test_candle(self, check_output: mock.MagicMock) -> None:
        """ Test with the sample real configuration. """
        check_output.return_value = JSON_CANDLEHOLDER.encode('UTF-8')
        self.do_test_real(
            exp_apps=[
                'entirely-different',
                'something',
                'something-else',
            ],
            exp_mach_type={
                'storage': ['0/lxd/1', '2/lxd/3'],
                'compute': ['0', '1'],
            },
            exp_sp_chosen={
                'storage': 'something',
                'compute': 'something-else',
            },
            exp_sp_machines={
                'compute': ['0', '1'],
                'candleholder': ['2'],
            })

    @mock.patch('subprocess.check_output')
    def test_real(self, check_output: mock.MagicMock) -> None:
        """ Test with the sample real configuration. """
        check_output.return_value = JSON_REAL.encode('UTF-8')
        self.do_test_real(
            exp_apps=[
                'entirely-different',
                'something',
                'something-else',
            ],
            exp_mach_type={
                'storage': ['0/lxd/1', '1/lxd/0'],
                'compute': ['0', '1'],
            },
            exp_sp_chosen={
                'storage': 'something',
                'compute': 'something-else',
            },
            exp_sp_machines={
                'compute': ['0', '1'],
            })


class TestDeploy(unittest.TestCase):
    """ Test get_deploy_actions(). """

    @mock.patch('subprocess.check_output')
    def test_actions_real(self, check_output: mock.MagicMock) -> None:
        """ Test get_deploy_actions() with the sample real config. """
        check_output.return_value = JSON_REAL.encode('UTF-8')
        res = cjuju.get_status()
        cfg = cconfig.Config(basedir='/base', subdir='subdir')
        commands = [act.command for act in cjuju.get_deploy_actions(cfg, res)]
        self.assertEqual(commands, [
            ['printf', '--', '%s', 'Deploying the storpool-block charm'],
            ['juju', 'deploy', '--',
             '/base/built/xenial/storpool-block/xenial/storpool-block'],
            ['printf', '--', '%s',
             'Linking the storpool-block charm with the something-else charm'],
            ['juju', 'add-relation', '--',
             'something-else:juju-info', 'storpool-block:juju-info'],
            ['printf', '--', '%s',
             'Apparently Cinder and Nova are on the same machines; '
             'skipping the storpool-candleholder deployment'],
            ['printf', '--', '%s', 'Deploying the cinder-storpool charm'],
            ['juju', 'deploy', '--',
             '/base/built/xenial/cinder-storpool/xenial/cinder-storpool'],
            ['printf', '--', '%s',
             'Linking the cinder-storpool charm with the something charm'],
            ['juju', 'add-relation', '--',
             'something:storage-backend', 'cinder-storpool:storage-backend'],
            ['printf', '--', '%s',
             'Linking the cinder-storpool charm with '
             'the storpool-block charm'],
            ['juju', 'add-relation', '--',
             'storpool-block:storpool-presence',
             'cinder-storpool:storpool-presence'],
            ['printf', '--', '%s',
             'The StorPool charms were deployed from /base/subdir'],
            ['printf', '--', '%s', ''],
        ])


class TestStorPoolConfig(unittest.TestCase):
    """ Test get_storpool_config_data(). """

    @mock.patch('subprocess.check_output')
    def test_config_data(self, check_output: mock.MagicMock) -> None:
        """ Test the build of the StorPool config data dictionary. """
        cfg = cconfig.Config(space='storpool', repo_auth='jrl:secret')

        check_output.return_value = JSON_REAL.encode('UTF-8')
        status = cjuju.get_status()
        self.assertEqual(status['_meta']['sp']['machines'], {
            'compute': ['0', '1'],
        })

        next_mach = 0

        def dup_hostnames(cmd: List[str]) -> bytes:
            """ Return the same hostname for any machine. """
            nonlocal next_mach
            mid = str(next_mach)
            next_mach = next_mach + 1

            self.assertEqual(cmd, ['juju', 'ssh', mid, 'hostname'])
            return 'same-hostname'.encode('us-ascii')

        check_output.side_effect = dup_hostnames
        self.assertRaises(cjuju.StorPoolError,
                          cjuju.get_storpool_config_data, cfg, status)

        def ssh_hostnames(cmd: List[str]) -> bytes:
            """ Mock a 'juju ssh <mach> hostname' invocation. """
            nonlocal next_mach
            mid = str(next_mach)
            next_mach = next_mach + 1

            self.assertEqual(cmd, ['juju', 'ssh', mid, 'hostname'])
            return ('srv' + mid).encode('us-ascii')

        check_output.side_effect = ssh_hostnames
        next_mach = 0
        data = cjuju.get_storpool_config_data(cfg, status)
        self.assertEqual(data, {
            'srv0': {
                'SP_OURID': '40',
                'SP_IFACE': 'enp2s0',
            },

            'srv1': {
                'SP_OURID': '41',
                'SP_IFACE': 'eth0.403',
            },
        })

        charm = cjuju.get_charm_config_data(cfg, status, 'SPCONFIG', [])
        self.assertEqual(charm, {
            'cinder-storpool': {
                'storpool_template': 'hybrid-r3',
            },

            'storpool-block': {
                'handle_lxc': True,
                'storpool_conf': 'SPCONFIG',
                'storpool_openstack_version': '1.5.0-1~1ubuntu1',
                'storpool_repo_url':
                    'http://jrl:secret@repo.storpool.com/storpool-maas/',
                'storpool_version': '18.01',
            },
        })
