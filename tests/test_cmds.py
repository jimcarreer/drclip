import pytest
import responses
from click.testing import CliRunner

from drclip.cmds import drclip, reg_tab

from tests.mocks import MockCredentials, mock_pages

REPO_ENTRIES = ['repo1/thing', 'repo2/thing', 'repo3/thing']
TAGS = ['1.0.0', 'latest', 'stable', '1.0.3', '2.0.0', 'unstable', 'rc']


def test_creds_not_found(mock_creds, runner: CliRunner):
    """Tests that when a registry specified with -r doesn't have credentials a useful error is displayed"""
    res = runner.invoke(drclip, ['-r', 'doesnt.exist.com', 'repos'])
    assert res.exit_code == 1
    assert 'could not be located (you may need to run docker login ... )' in res.stdout


def test_creds_strange_error(mock_strange_creds, runner: CliRunner):
    """Tests that when a registry specified with -r registry has a strange failure its wrapped / displayed"""
    res = runner.invoke(drclip, ['-r', 'doesnt.exist.com', 'repos'])
    assert res.exit_code == 1
    assert 'Unknown error when calling' in res.stdout


@pytest.mark.parametrize('args, n', [
    ([], 100),
    (['-p', '2'], 2),
    (['--page_size', '2'], 2)
])
def test_list_catalog(mock_creds: dict, runner: CliRunner, args: list, n: int):
    """Test drclip -r <registry> repos ... command"""
    with responses.RequestsMock() as rm:
        rm.add('GET', f'https://{MockCredentials.REPO}/v2/', body='{}')
        mock_pages(rm, f'https://{MockCredentials.REPO}', '/v2/_catalog', n, 'repositories', REPO_ENTRIES)
        res = runner.invoke(drclip, ['-r', 'test.com', 'repos']+args)
        assert res.exit_code == 0
        assert all(r in res.stdout for r in REPO_ENTRIES)


@pytest.mark.parametrize('incomplete, expected', [
    ('tes', ['test.com']),
    ('nota', []),
    ('test.com', ['test.com'])
])
def test_reg_tab(mock_creds, incomplete: str, expected: list):
    """Tests the tab completion helper for registry names works"""
    assert reg_tab(None, ['-r'], incomplete) == expected


@pytest.mark.parametrize('args, n, repo', [
    (['some/repo'], 100, 'some/repo'),
    (['some/repo', '-p', 2], 2, 'some/repo'),
    (['some/repo', '--page_size', 2], 2, 'some/repo'),
])
def test_list_tags(mock_creds: dict, runner: CliRunner, args: list, n: int, repo: str):
    """Test drclip -r <registry> tags <repository> command"""
    with responses.RequestsMock() as rm:
        rm.add('GET', f'https://{MockCredentials.REPO}/v2/', body='{}')
        mock_pages(rm, f'https://{MockCredentials.REPO}', f'/v2/{repo}/tags/list', n, 'tags', TAGS)
        res = runner.invoke(drclip, ['-r', 'test.com', 'tags']+args)
        assert res.exit_code == 0
        assert all(r in res.stdout for r in TAGS)


def test_list_tags_404(mock_creds: dict, runner: CliRunner):
    """Test drclip -r <registry> tags <repository> command handles 404"""
    with responses.RequestsMock() as rm:
        rm.add('GET', f'https://{MockCredentials.REPO}/v2/', body='{}')
        rm.add('GET', f'https://{MockCredentials.REPO}/v2/not/found/tags/list?n=100', status=404)
        res = runner.invoke(drclip, ['-r', 'test.com', 'tags', 'not/found'])
        assert res.exit_code == 1
        assert all(m in res.stdout for m in ['API return 404 for', '(does it exist?)'])


def test_list_tags_unexpected(mock_creds: dict, runner: CliRunner):
    """Test drclip -r <registry> tags <repository> command re-raises non 404"""
    with responses.RequestsMock() as rm:
        rm.add('GET', f'https://{MockCredentials.REPO}/v2/', body='{}')
        rm.add('GET', f'https://{MockCredentials.REPO}/v2/not/found/tags/list?n=100', status=500)
        res = runner.invoke(drclip, ['-r', 'test.com', 'tags', 'not/found'])
        assert res.exit_code == 1
