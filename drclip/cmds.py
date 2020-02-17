import json
import sys
from io import TextIOWrapper

import click
from requests import HTTPError

from drclip.creds import DockerCredentials, CredentialsNotFound, CredentialsException
from drclip.drapi import RegistryV2API, Paginated

REG_ENV = 'DRCLIP_REG'
REPO_ENV = 'DRCLIP_REPO'


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
@click.option('-r', '--registry', envvar=REG_ENV, type=click.STRING, help='The registry to query',
              autocompletion=reg_tab, required=True)
@click.pass_context
def drclip(ctx: click.core.Context, config: TextIOWrapper, registry: str):
    """Runs commands against docker registries"""
    ctx.obj = CmdContext(RegistryV2API(registry, DockerCredentials(config)))
    err = None
    try:
        ctx.obj.api.head()  # Simple version check / connectivity check
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
@click.option('-o', '--repository', type=click.STRING, envvar=REPO_ENV)
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


@drclip.command('manifest')
@click.option('-o', '--repository', type=click.STRING, envvar=REPO_ENV, required=True)
@click.option('-t', '--tag', type=click.STRING, required=True)
@pass_cmd_context
def show_manifest(ctx: CmdContext, repository: str, tag: str):
    """List the manifests for a given repository and a given tag"""
    api = f'{repository}/manifests/{tag}'
    try:
        click.echo(json.dumps(ctx.api.get(api), indent=2))
    except HTTPError as he:
        if he.response.status_code != 404:
            raise he
        click.echo(f'Error: API return 404 for {api} (do both the tag+repo exist?)', err=True)
        sys.exit(1)


@drclip.command('digests')
@click.option('-o', '--repository', type=click.STRING, envvar=REPO_ENV)
@click.option('-i', '--ignore_unknown', is_flag=True, help='Don\'t halt on unknown repo+tags, ignore and continue')
@click.argument('tags', type=click.STRING, required=True, nargs=-1)
@pass_cmd_context
def list_digest(ctx: CmdContext, repository: str, tags: list, ignore_unknown: bool):
    """Get the digest(s) for given tag(s)"""
    for tag in tags:
        api = f'{repository}/manifests/{tag}'
        try:
            click.echo(ctx.api.head(api)['Docker-Content-Digest'])
        except HTTPError as he:
            if he.response.status_code != 404:
                raise he
            elif ignore_unknown:
                continue
            click.echo(f'Error: API return 404 for {api} (do both the tag+repo exist?)', err=True)
            sys.exit(1)


@drclip.command('rmd')
@click.option('-o', '--repository', type=click.STRING, envvar=REPO_ENV)
@click.option('-i', '--ignore_unknown', is_flag=True, help='Don\'t halt on unknown repo+tags, ignore and continue')
@click.argument('digests', type=click.STRING, required=True, nargs=-1)
@pass_cmd_context
def remove_digest(ctx: CmdContext, repository: str, digests: list, ignore_unknown: bool):
    """Removes a manifest(s) for given digest(s)"""
    for digest in digests:
        api = f'{repository}/manifests/{digest}'
        try:
            click.echo(ctx.api.delete(api))
        except HTTPError as he:
            if he.response.status_code not in (404, 405):
                raise he
            elif he.response.status_code == 405:
                click.echo(f'Error: API return 405 for DELETE {api} (does the registry allow deletion?)', err=True)
                sys.exit(1)
            elif he.response.status_code == 404 and not ignore_unknown:
                click.echo(f'Error: API return 404 for {api} (do both the tag+repo exist?)', err=True)
                sys.exit(1)
