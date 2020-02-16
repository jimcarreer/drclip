import os
from pathlib import Path

import pytest

from drclip.creds import DockerCredentials, UnsupportedStore, CredentialsNotFound, CredentialsException

from tests.mocks import MockPopen

REGISTRY = 'my.private.docker.registry.com:443'
GOOD_CMD_GET = b'{"ServerURL":"","Username":"user","Secret":"pass"}'
BAD_REG_CMD_GET = b''
GOOD_DOCKER_CONFIG = """{
        "auths": {
            "my.private.docker.registry.com:443": {}
        },
        "HttpHeaders": {
            "User-Agent": "Docker-Client/18.09.7 (linux)"
        },
        "credsStore": "secretservice"
}"""


@pytest.fixture()
def fake_user_home(request, monkeypatch, tmpdir):
    docker_config = request.param if hasattr(request, 'param') else GOOD_DOCKER_CONFIG
    monkeypatch.setattr('drclip.creds.Path.expanduser', lambda p: Path(str(p).replace('~', str(tmpdir))))
    os.makedirs(f'{tmpdir}/.docker/')
    with open(f'{tmpdir}/.docker/config.json', 'w') as fh:
        fh.write(docker_config)
    yield tmpdir


def test_known(fake_user_home):
    """Tests DockerCredentials.known under expected environment"""
    assert DockerCredentials().known == [REGISTRY]


def test_get_credentials(fake_user_home):
    """Tests DockerCredentials.get_login under expected environment with registry"""
    with MockPopen.mock(target='drclip.creds.Popen') as mock:
        mock.add_cmd(['docker-credential-secretservice', 'get'], stdin=REGISTRY.encode(), stdout=GOOD_CMD_GET, rc=0)
        assert DockerCredentials().get_login(REGISTRY) == ('user', 'pass')


def test_get_credentials_when_passed_file(fake_user_home):
    """Tests DockerCredentials.get_login under expected environment with registry"""
    with MockPopen.mock(target='drclip.creds.Popen') as mock:
        mock.add_cmd(['docker-credential-secretservice', 'get'], stdin=REGISTRY.encode(), stdout=GOOD_CMD_GET, rc=0)
        with open(f'{fake_user_home}/someotherconfig.json', 'w+') as fh:
            fh.write(GOOD_DOCKER_CONFIG)
            fh.seek(0)
            assert DockerCredentials(config=fh).get_login(REGISTRY) == ('user', 'pass')


def test_credentials_not_found(fake_user_home):
    """Tests DockerCredentials.get_login raises properly when unknown registry supplied"""
    with MockPopen.mock(target='drclip.creds.Popen') as mock:
        mock.add_cmd(['docker-credential-secretservice', 'get'], stdin=b'test', stdout=b'credentials not found', rc=1)
        with pytest.raises(CredentialsNotFound, match='Credentials not found'):
            DockerCredentials().get_login('test')


def test_credentials_unknown_error(fake_user_home):
    """Tests DockerCredentials.get_login raises properly when the secret command returns 1 with a strange message"""
    with MockPopen.mock(target='drclip.creds.Popen') as mock:
        mock.add_cmd(['docker-credential-secretservice', 'get'], stdin=b'test', stdout=b'strange error', rc=1)
        with pytest.raises(CredentialsException, match=r'Unknown error when calling .+ strange error'):
            DockerCredentials().get_login('test')


@pytest.mark.parametrize('popen_except, match', [
    (PermissionError(), 'Permission denied'),
    (FileNotFoundError(), 'could not be found')
])
def test_credentials_popen_raise_rewrapped(fake_user_home, popen_except, match):
    """Tests DockerCredentials.get_login wraps common Popen errors correctly"""
    with MockPopen.mock(target='drclip.creds.Popen', raise_on_call=popen_except):
        with pytest.raises(CredentialsException, match=match):
            DockerCredentials().get_login('test')


@pytest.mark.parametrize('fake_user_home', [
    GOOD_DOCKER_CONFIG.replace('secretservice', 'osxkeychain'),
    GOOD_DOCKER_CONFIG.replace('secretservice', 'wincred'),
    GOOD_DOCKER_CONFIG.replace('secretservice', 'pass'),
    GOOD_DOCKER_CONFIG.replace('secretservice', 'notvalid'),
    GOOD_DOCKER_CONFIG.replace('secretservice', ''),
    GOOD_DOCKER_CONFIG.replace('secretservice', 'null'),
    GOOD_DOCKER_CONFIG.replace(',\n        "credsStore": "secretservice"', ''),
    '{}'
], indirect=True)
def test_unsupported_handling(fake_user_home):
    """Tests we handle unsupported credential stores with informative exception"""
    with pytest.raises(UnsupportedStore, match='not supported'):
        DockerCredentials().get_login(REGISTRY)

