"""
Test the storpool.charms.manage.actions classes.
"""


import unittest

from typing import Any, Dict, List, Type

import ddt  # type: ignore
import mock

from mypy_extensions import TypedDict

from storpool.charms.manage import actions as cact
from storpool.charms.manage import config as cconfig


ActionTestData = TypedDict('ActionTestData', {
    'cls': Type[cact.Action],
    'args': List[str],
    'kwargs': Dict[str, Any],
    'command': List[str],
})


TEST_ACTIONS = [
    ActionTestData({
        'cls': cact.ActComment,
        'args': ['Well hello there!'],
        'kwargs': {},
        'command': ['printf', '--', '%s', 'Well hello there!'],
    }),

    ActionTestData({
        'cls': cact.ActDeployCharm,
        'args': ['my-favorite-charm'],
        'kwargs': {},
        'command': [
            'juju', 'deploy', '--',
            '/base/built/weird/my-favorite-charm/weird/my-favorite-charm',
        ],
    }),

    ActionTestData({
        'cls': cact.ActDeployCharm,
        'args': ['my-favorite-charm'],
        'kwargs': {'to': ['huey', 'dewey', 'louie']},
        'command': [
            'juju', 'deploy', '-n', '3', '--to', 'huey,dewey,louie', '--',
            '/base/built/weird/my-favorite-charm/weird/my-favorite-charm',
        ],
    }),

    ActionTestData({
        'cls': cact.ActUpgradeCharm,
        'args': ['some-zany-charm'],
        'kwargs': {},
        'command': [
            'juju', 'upgrade-charm', '--path',
            '/base/built/weird/some-zany-charm/weird/some-zany-charm', '--',
            'some-zany-charm'
        ],
    }),

    ActionTestData({
        'cls': cact.ActUndeployCharm,
        'args': ['outdated-and-outpaced'],
        'kwargs': {},
        'command': [
            'juju', 'remove-application', '--', 'outdated-and-outpaced'
        ],
    }),

    ActionTestData({
        'cls': cact.ActAddRelation,
        'args': ['me:here', 'you:there'],
        'kwargs': {},
        'command': [
            'juju', 'add-relation', '--', 'me:here', 'you:there'
        ],
    }),
]


class ActionTest:
    """ Run a test on a single action. """

    def __init__(self,
                 testcase: unittest.TestCase,
                 cfg: cconfig.Config,
                 data: ActionTestData) -> None:
        """ Store everything and create the action object. """
        self.testcase = testcase
        self.cfg = cfg
        self.data = data
        cls = data['cls']
        args = data['args']
        kwargs = data['kwargs']
        self.action = cls(cfg, *args, **kwargs)  # type: ignore

    def check_command(self) -> None:
        """ Check whether the action's command is correct. """
        self.testcase.assertEqual(self.action.command, self.data['command'])

    def check_noop(self,
                   mock_call: mock.MagicMock,
                   mock_print: mock.MagicMock) -> None:
        """ Check whether a no-op operation really does nothing. """
        assert self.cfg.noop
        call_called = mock_call.call_count
        print_called = mock_print.call_count
        self.action.run()
        self.testcase.assertEqual(mock_call.call_count, call_called)
        self.testcase.assertEqual(mock_print.call_count, print_called + 1)

    def check_real(self,
                   mock_call: mock.MagicMock,
                   mock_print: mock.MagicMock) -> None:
        """ Check whether a real operation really tries to run something. """
        assert not self.cfg.noop
        call_called = mock_call.call_count
        print_called = mock_print.call_count
        self.action.run()
        self.testcase.assertEqual(mock_call.call_count, call_called + 1)
        mock_call.assert_called_with(self.data['command'], shell=False)
        self.testcase.assertEqual(mock_print.call_count, print_called)


def build_cfg(noop: bool) -> cconfig.Config:
    """ Build a test configuration. """
    return cconfig.Config(
        basedir='/base',
        subdir='sub',
        baseurl='/repo',
        branches_file='/conf/test-branches.yaml',
        noop=noop,
        series='weird',
        space='outer',
        repo_auth='jrl:secret',
    )


@ddt.ddt
class TestActions(unittest.TestCase):
    """ Test some action classes. """

    @mock.patch('builtins.print')
    @mock.patch('subprocess.check_call')
    @ddt.data(*TEST_ACTIONS)
    def test_noop(self,
                  data: ActionTestData,
                  mock_call: mock.MagicMock,
                  mock_print: mock.MagicMock) -> None:
        cfg = build_cfg(noop=True)
        atest = ActionTest(self, cfg, data)
        atest.check_command()
        atest.check_noop(mock_call, mock_print)

    @mock.patch('builtins.print')
    @mock.patch('subprocess.check_call')
    @ddt.data(*TEST_ACTIONS)
    def test_real(self,
                  data: ActionTestData,
                  mock_call: mock.MagicMock,
                  mock_print: mock.MagicMock) -> None:
        cfg = build_cfg(noop=False)
        atest = ActionTest(self, cfg, data)
        atest.check_command()
        atest.check_real(mock_call, mock_print)
