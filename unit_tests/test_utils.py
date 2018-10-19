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
Unit tests for the storpool.charms.manage.utils module.
"""

import builtins
import unittest

import mock

from storpool.charms.manage import config as cconfig
from storpool.charms.manage import utils as cu


class TestSPMsg(unittest.TestCase):
    """
    A trivial test for the sp_msg() function.
    """

    @mock.patch('builtins.print')
    def test_sp_msg(self, print_function: mock.MagicMock) -> None:
        """
        Make sure that sp_msg() invokes print().
        """
        self.assertEqual(print_function.call_count, 0)
        cu.sp_msg('Hello world!')
        print_function.assert_called_once_with('Hello world!')
        builtins.print('We are indeed mocking print(), right?')
        print('Right?')
        cu.sp_msg('Something else')
        cu.sp_msg('And something more')
        self.assertEqual(print_function.call_count, 5)


class TestDirectories(unittest.TestCase):
    """
    Various tests for the directory-related functions.
    """

    @mock.patch('os.chdir')
    @mock.patch('storpool.charms.manage.utils.sp_msg')
    def test_chdir(self,
                   sp_msg: mock.MagicMock,
                   os_chdir: mock.MagicMock) -> None:
        """
        Test the chdir() function with various sets of arguments.
        """

        # Test no-op mode first.
        cfg = cconfig.Config(noop=True)

        cu.sp_chdir(cfg, '/path')
        self.assertEqual(sp_msg.call_count, 1)
        self.assertEqual(os_chdir.call_count, 0)

        cu.sp_chdir(cfg, '/path', do_chdir=False)
        self.assertEqual(sp_msg.call_count, 2)
        self.assertEqual(os_chdir.call_count, 0)

        cu.sp_chdir(cfg, '/path', do_chdir=True)
        self.assertEqual(sp_msg.call_count, 3)
        self.assertEqual(os_chdir.call_count, 1)

        # And now for the real thing.
        cfg = cconfig.Config()

        cu.sp_chdir(cfg, '/path')
        self.assertEqual(sp_msg.call_count, 3)
        self.assertEqual(os_chdir.call_count, 2)

        cu.sp_chdir(cfg, '/path', do_chdir=False)
        self.assertEqual(sp_msg.call_count, 3)
        self.assertEqual(os_chdir.call_count, 3)

        cu.sp_chdir(cfg, '/path', do_chdir=True)
        self.assertEqual(sp_msg.call_count, 3)
        self.assertEqual(os_chdir.call_count, 4)
