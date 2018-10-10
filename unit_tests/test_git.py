"""
Unit tests for the storpool.charms.manage.git module.
"""


import unittest

from typing import Callable, List, Tuple

import mock

from storpool.charms.manage import config as cconfig
from storpool.charms.manage import git as cgit


class Event(object):
    """ A single mocked function call. """

    def __init__(self, name: str, args: Tuple) -> None:
        """ Store the function call data. """
        self._name = name
        self._args = args

    @property
    def name(self) -> str:
        """ Get the name of the called function. """
        return self._name

    @property
    def args(self) -> Tuple:
        """ Get the arguments the function was called with. """
        return self._args

    def __str__(self) -> str:
        """ Return a human-readable representation. """
        return '{name}({args})' \
               .format(name=self._name, args=', '.join(self._args))

    def __repr__(self) -> str:
        """ Return a Python-esque representation. """
        return '{tname}(name={name}, args={args})' \
               .format(tname=type(self).__name__,
                       name=repr(self._name),
                       args=repr(self._args))

    def __eq__(self, other: object) -> bool:
        """ Check if two events are the same, ignoring sp_msg() arguments. """
        if not isinstance(other, Event):
            return False
        event = other  # type: Event

        if self.name != event.name:
            return False

        if self.name == 'sp_msg':
            if len(self.args) == 0 or len(event.args) == 0:
                return True
        return self.args == event.args


def append_event_fn(events: List[Event], name: str) -> Callable[..., None]:
    """ Return a function that will record its invocation. """
    def _inner(*args: Tuple) -> None:
        """ Record the function invocation. """
        events.append(Event(name=name, args=args))

    return _inner


def add_events_scm_utils(obj: mock.MagicMock, events: List[Event]) -> None:
    """ Mock the s.c.m.utils functions. """
    for name in ('sp_msg', 'sp_chdir', 'sp_mkdir', 'sp_makedirs', 'sp_run'):
        setattr(obj, name, append_event_fn(events, name))


class TestGit(unittest.TestCase):
    @mock.patch('storpool.charms.manage.git.cu')
    def test_checkout(self, mod_utils: mock.MagicMock) -> None:
        events = []  # type: List[Event]
        add_events_scm_utils(mod_utils, events)
        cfg = cconfig.Config(baseurl='.')
        cgit.checkout(cfg, 'charm-storpool-block')

        self.assertEqual(events, [
            Event(name='sp_msg', args=()),
            Event(name='sp_run', args=(
                cfg,
                ['git', 'clone', '-b', 'master', '--',
                 './charm-storpool-block.git']
            )),
        ])

        def record_and_raise(*args: Tuple) -> None:
            """ Record the call and raise an exception. """
            events.append(Event(name='sp_run', args=args))
            raise IOError()

        events.clear()
        mod_utils.sp_run = record_and_raise
        cfg = cconfig.Config(baseurl='http://repo')
        cfg.set_branches({'charm-other': 'devel'})
        with self.assertRaises(cgit.RepoCheckoutError) as err:
            cgit.checkout(cfg, 'charm-other')

        self.assertEqual(events, [
            Event(name='sp_msg', args=()),
            Event(name='sp_run', args=(
                cfg,
                ['git', 'clone', '-b', 'devel', '--',
                 'http://repo/charm-other.git']
            )),
        ])
        self.assertIsInstance(err.exception.error, IOError)
