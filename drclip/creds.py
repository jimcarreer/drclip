import json
from io import TextIOWrapper
from subprocess import PIPE, Popen
from pathlib import Path
from typing import Union, List


class CredentialsException(Exception):
    """Base exception class for credential issues"""
    pass


class UnsupportedStore(CredentialsException):
    """Raised when the backing credential store is not supported"""
    pass


class CredentialsNotFound(CredentialsException):
    """Raised when credentials for a registry are not found in the store"""
    pass


class DockerCredentials:
    """Wraps credential retrieval"""

    _DEFAULT_LOCATION = '~/.docker/config.json'
    _SUPPORTED_STORES = {'secretservice'}

    def __init__(self, config: Union[str, Path, TextIOWrapper] = None):
        """
        Initializes the DockerCredentials class

        :param config: (optional) specifies configuration file location to read, defaults to ~/.docker/config.json
        """
        if not isinstance(config, TextIOWrapper):
            config = Path(config) if config else Path(self._DEFAULT_LOCATION)
            config = config.expanduser().absolute()
            with open(config, 'r') as fp:
                self._config = json.load(fp)
        else:
            self._config = json.load(config)
        self._store = self._config.get('credsStore', None)
        if self._store not in self._SUPPORTED_STORES:
            raise UnsupportedStore(f'Credential store "{self._store}" not supported')
        # TODO: Support the other methods besides secretservice when we can actually test with them
        self._cmd = ['docker-credential-secretservice', 'get']

    @property
    def known(self) -> List[str]:
        """
        Returns the URL for the known

        :return: list of known registries as defined by the configuration
        """
        return [k for k in self._config.get('auths', {}).keys()]

    def get_login(self, registry: str) -> (str, str):
        """
        Get the user name a password for the given repo

        :param registry: the docker registry as a URL to get the credentials for
        :return: a tuple where the first element is the registry user and the second element is the user's password
        """
        try:
            service = Popen(self._cmd, stderr=PIPE, stdout=PIPE, stdin=PIPE)
        except FileNotFoundError:
            raise CredentialsException(f'The command {self._cmd[0]} could not be found')
        except PermissionError:
            raise CredentialsException(f'Permission denied when trying to call {self._cmd[0]}')
        out, _ = service.communicate(input=registry.encode())
        out = out.decode('utf-8')
        if service.returncode > 0 and 'credentials not found' in out:
            raise CredentialsNotFound(f'Credentials not found for {registry}')
        elif service.returncode > 0:
            raise CredentialsException(f'Unknown error when calling docker-credential-service {out}')
        out = json.loads(out)
        return out['Username'], out['Secret']
