import sys
from io import TextIOWrapper

import click
from requests import HTTPError

from drclip.__version__ import __version__
from drclip.creds import DockerCredentials, CredentialsNotFound, CredentialsException
from drclip.drapi import RegistryV2API, Paginated


class CmdContext:
    def __init__(self, api: RegistryV2API):
        self.api = api


pass_cmd_context = click.make_pass_decorator(CmdContext, ensure=True)


def reg_tab(ctx: click.core.Context, args: list, incomplete: str) -> list:
    """Tab completion helper for registry argument"""
    credentials = DockerCredentials()
    return [r for r in credentials.known if incomplete in r]


@click.group()
@click.option('-c', '--config', type=click.File('r'))
@click.option('-r', '--registry', type=click.STRING, help='The registry to query', autocompletion=reg_tab)
@click.pass_context
def drclip(ctx: click.core.Context, config: TextIOWrapper, registry: str):
    """Runs commands against docker registries"""
    ctx.obj = CmdContext(RegistryV2API(registry, DockerCredentials(config)))
    try:
        # Simple version check / connectivity check
        ctx.obj.api.get()
        err = None
    except CredentialsNotFound:
        err = f'Error: Credentials for {registry} could not be located (you may need to run docker login ... )'
    except CredentialsException as e:
        err = e
    if err:
        click.echo(err, err=True)
        sys.exit(1)


@drclip.command('repos')
@click.option('-p', '--page_size', type=click.IntRange(1), help='Size of page to retrieve', default=100)
@pass_cmd_context
def list_catalogue(ctx: CmdContext, page_size: int):
    """Lists the repositories in a registry via the _catalog API"""
    pager = Paginated(ctx.api, '_catalog', params={'n': page_size})
    for page in pager:
        for repo in page['repositories']:
            click.echo(repo)


@drclip.command('tags')
@click.argument('repository', type=click.STRING)
@click.option('-p', '--page_size', type=click.IntRange(1), help='Size of page to retrieve', default=100)
@pass_cmd_context
def list_tags(ctx: CmdContext, repository: str, page_size: int):
    """Lists the tags for a given repository using the /tags/list API"""
    # So, docker claims this endpoint is paginated like _catalog:
    # https://docs.docker.com/registry/spec/api/#listing-image-tags
    # but this does not appear to be the case, in any event, using the pager is fine here in case they ever start
    pager = Paginated(ctx.api, f'{repository}/tags/list', params={'n': page_size})
    try:
        for page in pager:
            for tag in page['tags']:
                click.echo(tag)
    except HTTPError as he:
        if he.response.status_code != 404:
            raise he
        click.echo(f'Error: API return 404 for {repository} (does it exist?)', err=True)
        sys.exit(1)
