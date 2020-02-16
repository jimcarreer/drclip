import pytest

from drclip.drapi import RegistryV2API, UnexpectedPageLink, Paginated


def test_idiot_guardrails(mock_creds):
    """Tests raw requests stops stupid"""
    api = RegistryV2API('test.com')
    with pytest.raises(ValueError, match='Bad HTTP method'):
        api.raw_request('UPSERT', 'iam/idiot')


@pytest.mark.parametrize('link', [
    '</v2/mising/rel>; ',
    '<junk/api>; rel="next"',
    'SOME WEIRD SHIT'
])
def test_strange_next_link(link):
    with pytest.raises(UnexpectedPageLink, match='Strange link header'):
        Paginated.extract_next(link)
