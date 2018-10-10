"""
Handle Git operations.
"""


import abc

from . import config as cconfig
from . import utils as cu


class RepoError(Exception, metaclass=abc.ABCMeta):
    """ A base class for errors that may occur during Git operations. """

    def __init__(self, name: str, error: Exception) -> None:
        """ Initialize an error object. """
        self._name = name
        self._error = error

    @property
    def name(self) -> str:
        """ Return the name of the Git repository. """
        return self._name

    @property
    def error(self) -> Exception:
        """ Return the error that occurred. """
        return self._error

    @abc.abstractproperty
    def action(self) -> str:
        """ Return a human-readable name for the action that failed. """
        raise NotImplementedError()

    def __str__(self) -> str:
        """ Provide a human-readable representation of an error. """
        return 'Could not {act} the Git repository {name}: {err}' \
               .format(act=self.action, name=self._name, err=self._error)

    def __repr__(self) -> str:
        """ Provide a Python-esque representation of an error. """
        return '{tname}(name={name}, error={error})' \
               .format(tname=type(self).__name__, name=self._name,
                       error=self._error)


class RepoCheckoutError(RepoError):
    """ An error that occurred while checking out a repository. """

    @property
    def action(self) -> str:
        """ This error occurred while checking out. """
        return 'check out'


def checkout(cfg: cconfig.Config, name: str) -> None:
    """ Check out a single Git repository. """
    url = '{base}/{name}.git'.format(base=cfg.baseurl, name=name)
    branch = cfg.branches.get(name, 'master')
    cu.sp_msg('Checking out {url} branch {branch}'
              .format(url=url, branch=branch))
    try:
        cu.sp_run(cfg, ['git', 'clone', '-b', branch, '--', url])
    except Exception as err:
        raise RepoCheckoutError(name, err)
