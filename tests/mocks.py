import copy
import json
import contextlib
import collections
from urllib.parse import urlparse

import responses

from drclip.creds import CredentialsNotFound, CredentialsException

from unittest import mock as std_mock


def mock_pages(mock: responses.RequestsMock, base_url: str, api: str, page_size: int, entry_name: str, entries: list):
    """
    Setups up mock responses for multiple pages

    :param mock: request mock to add mock requests too
    :param base_url: the base url of the paginated responses
    :param api: the api that is being paginated
    :param page_size: the size of the pages to make
    :param entry_name: the element on the json response that page entries appear
    :param entries: the full list of entries to paginate
    :return: the given mock object updated with mocked page responses
    """
    assert page_size > 0, 'page_size must be greater than 0'
    assert len(entries) > 0, 'entries must not be empty'
    url = urlparse(base_url)
    start = 0
    end = page_size
    last = None
    page_entries = entries[start:end]
    while page_entries:
        d = {entry_name: copy.deepcopy(page_entries)}
        q = (url.query + '&' if url.query else '') + f'n={page_size}' + (f'&last={last}' if last else '')
        start += page_size
        end += page_size
        last = None
        headers = None
        if entries[start:end]:
            last = page_entries[-1]
            nq = (url.query + '&' if url.query else '') + f'n={page_size}' + f'&last={last}' if last else ''
            headers = {'Link': f'<{api}?{nq}>; rel="next"'}
        page_entries = entries[start:end]
        mock.add('GET', f'{base_url}/{api.strip("/")}?{q}', json.dumps(d), match_querystring=True, headers=headers)


class MockCredentialsStrange:
    """Mocks the DockerCredential store when we get a weird error from the store helper"""

    def __init__(self, *args, **kwargs):
        pass

    def get_login(self, registry: str) -> (str, str):
        raise CredentialsException(f'Unknown error when calling docker-credential-service strange error message')


class MockCredentials:
    """Mocks the DockerCredential class"""

    REG = 'test.com'
    AUTHS = {'test.com': ('user', 'pass')}

    def __init__(self, *args, **kwargs):
        pass

    @property
    def known(self) -> list:
        return [k for k in self.AUTHS.keys()]

    def get_login(self, registry: str) -> (str, str):
        if registry in self.AUTHS:
            return self.AUTHS[registry]
        raise CredentialsNotFound(f'Credentials not found for {registry}')


class MockPopen:
    """
    Allows for the mocking of subprocess.Popen()

    Usage:
        with MockPopen.mock() as mock:
            mock.add_cmd(['echo', '"tacos"'], stdout=b'tacos', rc=0)
            child = subprocess.Popen(['echo', '"tacos"'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = child.communicate()
            assert stdout == b'tacos'
            assert stderr == b''
            assert child.returncode == 0
    """

    class MockSubprocess:
        """Mock child process to be returned from calls to Popen()"""

        def __init__(self, stdin: bytes = b'', stdout: bytes = b'', stderr: bytes = b'', rc: int = 0):
            self._stdout = stdout
            self._stderr = stderr
            self._expected_stdin = stdin
            self._rc = rc

        @property
        def returncode(self) -> int:
            return self._rc

        def communicate(self, input: bytes) -> (bytes, bytes):
            assert input == self._expected_stdin, 'The input provided for subprocess does not match the expected input'
            return self._stdout, self._stderr

    @staticmethod
    @contextlib.contextmanager
    def mock(assert_all_called: bool = True, target: str = 'subprocess.Popen', raise_on_call: Exception = None):
        mocker = MockPopen(raise_on_call)
        patcher = std_mock.patch(target=target, new=mocker)
        patcher.start()
        yield mocker
        patcher.stop()
        if assert_all_called:
            assert mocker.uncalled == 0, f'There were {mocker.uncalled} commands'

    def __init__(self, raise_on_call: Exception = None):
        self._raise_on_call = raise_on_call
        self._cmds = collections.defaultdict(list)

    @property
    def uncalled(self) -> int:
        uncalled = 0
        for cmd in self._cmds:
            uncalled += len(self._cmds[cmd])
        return uncalled

    def add_cmd(self, cmd: list, stdin: bytes = b'', stdout: bytes = b'', stderr: bytes = b'', rc: int = 0):
        cmd = tuple(cmd)
        self._cmds[cmd].append(MockPopen.MockSubprocess(stdin=stdin, stdout=stdout, stderr=stderr, rc=rc))

    def __call__(self, *args, **kwargs) -> MockSubprocess:
        if self._raise_on_call:
            raise self._raise_on_call
        cmd = tuple(args[0])
        assert cmd in self._cmds, f'The command {cmd} was not mocked'
        assert self._cmds[cmd], f'Exhausted mocked command responses for {cmd}'
        return self._cmds[cmd].pop()
