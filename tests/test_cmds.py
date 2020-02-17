import pytest
import responses
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner

from drclip.cmds import drclip, reg_tab, REG_ENV, REPO_ENV

from tests.mocks import MockCredentials, mock_pages

TEST_REG = MockCredentials.REG
TEST_REPO = 'some/repo'
TEST_TAG = 'testing-tag'
REPO_ENTRIES = ['repo1/thing', 'repo2/thing', 'repo3/thing']
TAGS = ['1.0.0', 'latest', 'stable', '1.0.3', '2.0.0', 'unstable', 'rc']
TEST_DIGEST = 'sha256:b39ccc3481b9af431027f90dfb3e5f102e1ceb54686ce1815696940524b5f438'


class TestContext:
    def __init__(self, creds: dict, patcher: MonkeyPatch):
        self.creds = creds
        self.runner = CliRunner()
        self.patcher = patcher


@pytest.fixture()
def tctx(monkeypatch: MonkeyPatch):
    """Main test context"""
    monkeypatch.setattr('drclip.drapi.DockerCredentials', MockCredentials)
    monkeypatch.setattr('drclip.cmds.DockerCredentials', MockCredentials)
    yield TestContext(creds=MockCredentials.AUTHS, patcher=monkeypatch)


def test_creds_not_found(tctx: TestContext):
    """Tests that when a registry specified with -r doesn't have credentials a useful error is displayed"""
    res = tctx.runner.invoke(drclip, ['-r', 'doesnt.exist.com', 'repos'])
    assert res.exit_code == 1
    assert 'could not be located (you may need to run docker login ... )' in res.stdout


def test_creds_strange_error(mock_strange_creds, runner: CliRunner):
    """Tests that when a registry specified with -r registry has a strange failure its wrapped / displayed"""
    res = runner.invoke(drclip, ['-r', 'doesnt.exist.com', 'repos'])
    assert res.exit_code == 1
    assert 'Unknown error when calling' in res.stdout


@pytest.mark.parametrize('incomplete, expected', [
    ('tes', ['test.com']),
    ('nota', []),
    ('test.com', ['test.com'])
])
def test_reg_tab(mock_creds, incomplete: str, expected: list):
    """Tests the tab completion helper for registry names works"""
    assert reg_tab(None, ['-r'], incomplete) == expected


@pytest.mark.parametrize('bargs, benvs', [
    (['-r', TEST_REG], {}),
    (['--registry', TEST_REG], {}),
    ([], {REG_ENV: TEST_REG})
])
class TestCommands:

    @staticmethod
    def mock_hc(rm: responses.RequestsMock):
        rm.add('HEAD', f'https://{TEST_REG}/v2/')
        return rm

    @staticmethod
    def set_envs(patcher: MonkeyPatch, benvs: dict = None, envs: dict = None):
        benvs = {} if not benvs else benvs
        envs = {} if not envs else envs
        benvs.update(envs)
        for env in benvs:
            patcher.setenv(env, benvs[env])

    @pytest.mark.parametrize('args, n', [
        (['repos'], 100),
        (['repos', '-p', '2'], 2),
        (['repos', '--page_size', '2'], 2)
    ])
    def test_list_catalog(self, tctx: TestContext, bargs: list, args: list, n: int, benvs: dict):
        """Test repos sub command"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            mock_pages(rm, f'https://{TEST_REG}', '/v2/_catalog', n, 'repositories', REPO_ENTRIES)
            self.set_envs(tctx.patcher, benvs)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 0
            assert all(r in res.stdout for r in REPO_ENTRIES)

    @pytest.mark.parametrize('args, n, envs', [
        (['tags', '-o', TEST_REPO], 100, {}),
        (['tags', '-o', TEST_REPO, '-p', 2], 2, {}),
        (['tags', '-o', TEST_REPO, '--page_size', 2], 2, {}),
        (['tags'], 100, {REPO_ENV: TEST_REPO}),
        (['tags', '-p', 2], 2, {REPO_ENV: TEST_REPO}),
        (['tags', '--page_size', 2], 2, {REPO_ENV: TEST_REPO}),
    ])
    def test_list_tags(self, tctx: TestContext, bargs: list, args: list, n: int, benvs: dict, envs: dict):
        """Tests tags sub command"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            mock_pages(rm, f'https://{TEST_REG}', f'/v2/{TEST_REPO}/tags/list', n, 'tags', TAGS)
            self.set_envs(tctx.patcher, benvs, envs)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 0
            assert all(r in res.stdout for r in TAGS)

    @pytest.mark.parametrize('args, envs, code, match', [
        (['tags', '-o', 'bad/repo'], {}, 404, 'does it exist?'),
        (['tags', '--repository', 'bad/repo'], {}, 404, 'does it exist?'),
        (['tags'], {REPO_ENV: 'bad/repo'}, 404, 'does it exist?'),
        (['tags', '-o', 'bad/repo'], {}, 500, ''),
        (['tags', '--repository', 'bad/repo'], {}, 500, ''),
        (['tags'], {REPO_ENV: 'bad/repo'}, 500, ''),
    ])
    def test_list_tags_handles_err(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict, code: int,
                                   match: str):
        """Test tags sub command handles 404"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('GET', f'https://{TEST_REG}/v2/bad/repo/tags/list?n=100', status=code)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 1
            assert match in res.stdout

    @pytest.mark.parametrize('args, envs', [
        (['manifest', '-o', TEST_REPO, '-t', TEST_TAG], {}),
        (['manifest', '--tag', TEST_TAG], {REPO_ENV: TEST_REPO}),
    ])
    def test_show_manifest(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict):
        """Tests manifest sub command"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('GET', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}', body='{"payload": "manifest"}')
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 0
            assert all(m for m in ['payload', 'manifest'])

    @pytest.mark.parametrize('args, envs, code, match', [
        (['manifest', '-o', TEST_REPO, '-t', 'bad-tag'], {}, 404, 'do both the tag+repo exist?'),
        (['manifest', '--tag', 'bad-tag'], {REPO_ENV: TEST_REPO}, 404, 'do both the tag+repo exist?'),
        (['manifest', '-o', TEST_REPO, '-t', 'bad-tag'], {}, 500, ''),
        (['manifest', '--tag', 'bad-tag'], {REPO_ENV: TEST_REPO}, 500, ''),
    ])
    def test_show_manifest_handles_err(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict,
                                       code: int, match: str):
        """Tests manifest sub command handles error"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('GET', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/bad-tag', status=code)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 1
            assert match in res.stdout

    @pytest.mark.parametrize('args, envs', [
        (['digests', '-o', TEST_REPO, TEST_TAG, TEST_TAG], {}),
        (['digests', TEST_TAG, TEST_TAG], {REPO_ENV: TEST_REPO})
    ])
    def test_list_digest(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict):
        """Tests digests sub command"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('HEAD', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}',
                   adding_headers={'Docker-Content-Digest': TEST_DIGEST})
            rm.add('HEAD', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}',
                   adding_headers={'Docker-Content-Digest': TEST_DIGEST})
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 0
            assert res.stdout.strip().split('\n') == [TEST_DIGEST, TEST_DIGEST]

    @pytest.mark.parametrize('args, envs', [
        (['digests', '-i', '-o', TEST_REPO, TEST_TAG, 'unknown-tag', TEST_TAG], {}),
        (['digests', '--ignore_unknown', '-o', TEST_REPO, TEST_TAG, 'unknown-tag', TEST_TAG], {}),
        (['digests', '-i', TEST_TAG, 'unknown-tag', TEST_TAG], {REPO_ENV: TEST_REPO}),
        (['digests', '--ignore_unknown', TEST_TAG, 'unknown-tag', TEST_TAG], {REPO_ENV: TEST_REPO})
    ])
    def test_list_digest_ignores(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict):
        """Tests digests sub command ignores 404s"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('HEAD', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}',
                   adding_headers={'Docker-Content-Digest': TEST_DIGEST})
            rm.add('HEAD', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}',
                   adding_headers={'Docker-Content-Digest': TEST_DIGEST})
            rm.add('HEAD', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/unknown-tag', status=404)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 0
            assert res.stdout.strip().split('\n') == [TEST_DIGEST, TEST_DIGEST]

    @pytest.mark.parametrize('args, envs, code, match', [
        (['digests', '-o', TEST_REPO, 'bad-tag'], {}, 404, 'do both the tag+repo exist?'),
        (['digests', 'bad-tag'], {REPO_ENV: TEST_REPO}, 404, 'do both the tag+repo exist?'),
        (['digests', '-o', TEST_REPO, 'bad-tag'], {}, 500, ''),
        (['digests', 'bad-tag'], {REPO_ENV: TEST_REPO}, 500, ''),
    ])
    def test_list_digest_handles_err(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict,
                                       code: int, match: str):
        """Tests digests sub command handles error"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('HEAD', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/bad-tag', status=code)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 1
            assert match in res.stdout

    @pytest.mark.parametrize('args, envs', [
        (['rmd', '-i', '-o', TEST_REPO, TEST_TAG, 'unknown-tag', TEST_TAG], {}),
        (['rmd', '--ignore_unknown', '-o', TEST_REPO, TEST_TAG, 'unknown-tag', TEST_TAG], {}),
        (['rmd', '-i', TEST_TAG, 'unknown-tag', TEST_TAG], {REPO_ENV: TEST_REPO}),
        (['rmd', '--ignore_unknown', TEST_TAG, 'unknown-tag', TEST_TAG], {REPO_ENV: TEST_REPO})
    ])
    def test_rmd_ignores(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict):
        """Tests rmd sub command ignores 404s"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('DELETE', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}',
                   adding_headers={'Docker-Content-Digest': TEST_DIGEST})
            rm.add('DELETE', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/{TEST_TAG}',
                   adding_headers={'Docker-Content-Digest': TEST_DIGEST})
            rm.add('DELETE', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/unknown-tag', status=404)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 0

    @pytest.mark.parametrize('args, envs, code, match', [
        (['rmd', '-o', TEST_REPO, 'bad-tag'], {}, 404, 'do both the tag+repo exist?'),
        (['rmd', 'bad-tag'], {REPO_ENV: TEST_REPO}, 404, 'do both the tag+repo exist?'),
        (['rmd', '-o', TEST_REPO, 'bad-tag'], {}, 500, ''),
        (['rmd', 'bad-tag'], {REPO_ENV: TEST_REPO}, 500, ''),
        (['rmd', '-o', TEST_REPO, 'bad-tag'], {}, 405, 'does the registry allow deletion?'),
        (['rmd', 'bad-tag'], {REPO_ENV: TEST_REPO}, 405, 'does the registry allow deletion?')
    ])
    def test_rmd_handles_err(self, tctx: TestContext, bargs: list, args: list, benvs: dict, envs: dict, code: int,
                             match: str):
        """Tests rmd sub command handles error"""
        with responses.RequestsMock() as rm:
            self.mock_hc(rm)
            self.set_envs(tctx.patcher, benvs, envs)
            rm.add('DELETE', f'https://{TEST_REG}/v2/{TEST_REPO}/manifests/bad-tag', status=code)
            res = tctx.runner.invoke(drclip, bargs + args)
            assert res.exit_code == 1
            assert match in res.stdout
