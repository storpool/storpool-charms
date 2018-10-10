"""
Unit tests for the storpool.charms.manage.config module.
"""


import unittest

import mock

from storpool.charms.manage import config as cconfig
from storpool.charms.manage import utils as cu


class TestConfig(unittest.TestCase):
    """ Test various aspects of the configuration object. """

    def test_init(self) -> None:
        """ Test the object initialization. """
        cfg = cconfig.Config()
        self.assertEqual(cfg.basedir, cconfig.DEFAULT_BASEDIR)
        self.assertEqual(cfg.subdir, cconfig.DEFAULT_SUBDIR)
        self.assertEqual(cfg.baseurl, cconfig.DEFAULT_BASEURL)
        self.assertIsNone(cfg.branches_file)

        self.assertEqual(cfg.branches, {})

    def test_parse(self) -> None:
        """ Test parsing the branches file. """
        cfg = cconfig.Config(branches_file='branches.yaml')

        def raise_oserror(fname: str, mode: str) -> None:
            """ Raise an OSError exception for testing purposes. """
            self.assertEqual(fname, 'branches.yaml')
            self.assertEqual(mode, 'r')
            raise OSError()

        mock_file = mock.mock_open()
        mock_file.side_effect = raise_oserror
        with mock.patch('storpool.charms.manage.utils.open', mock_file,
                        create=True):
            with self.assertRaises(cu.BranchesReadError) as err:
                cu.parse_branches_file(cfg)
            self.assertIsInstance(err.exception.error, OSError)

        mock_file = mock.mock_open(read_data='whee: 1: 2: 3:')
        with mock.patch('storpool.charms.manage.utils.open', mock_file,
                        create=True):
            self.assertRaises(cu.BranchesParseError,
                              cu.parse_branches_file, cfg)

        mock_file = mock.mock_open(read_data='whee')
        with mock.patch('storpool.charms.manage.utils.open', mock_file,
                        create=True):
            self.assertRaises(cu.BranchesValidateError,
                              cu.parse_branches_file, cfg)

        mock_file = mock.mock_open(read_data='branches:\n  c:\n    - 1')
        with mock.patch('storpool.charms.manage.utils.open', mock_file,
                        create=True):
            self.assertRaises(cu.BranchesValidateError,
                              cu.parse_branches_file, cfg)

        mock_file = mock.mock_open(read_data='''
branches:
  charm-storpool-block: assorted-fixes
  layer-storpool-openstack-integration: devel
''')
        with mock.patch('storpool.charms.manage.utils.open', mock_file,
                        create=True):
            branches = cu.parse_branches_file(cfg)
            self.assertEqual(branches, {
                'charm-storpool-block': 'assorted-fixes',
                'layer-storpool-openstack-integration': 'devel',
            })
