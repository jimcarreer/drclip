import pytest
from click.testing import CliRunner

from tests.mocks import MockCredentials, MockCredentialsStrange


@pytest.fixture()
def mock_creds(monkeypatch):
    monkeypatch.setattr('drclip.drapi.DockerCredentials', MockCredentials)
    monkeypatch.setattr('drclip.cmds.DockerCredentials', MockCredentials)
    yield MockCredentials.AUTHS


@pytest.fixture()
def mock_strange_creds(monkeypatch):
    monkeypatch.setattr('drclip.drapi.DockerCredentials', MockCredentialsStrange)
    monkeypatch.setattr('drclip.cmds.DockerCredentials', MockCredentialsStrange)
    yield


@pytest.fixture()
def runner() -> CliRunner:
    yield CliRunner()
