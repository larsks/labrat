import click
import gitlab
import subprocess

DEFAULT_GITLAB_URL = 'https://gitlab.com'
GITLAB_PROJECT_FEATURES = {
    'issues': 'issues_enabled',
    'jobs': 'jobs_enabled',
    'lfs': 'lfs_enabled',
    'merge-requests': 'merge_requests_enabled',
    'public-jobs': 'public_jobs',
    'registry': 'container_registry_enabled',
    'request-access': 'request_access_enabled',
    'shared-runners': 'shared_runners_enabled',
    'snippets': 'snippets_enabled',
    'wiki': 'wiki_enabled',
}


def git_config_value(key):
    try:
        value = subprocess.check_output(
            ['git', 'config', '--get', key]
        ).strip()
    except subprocess.CalledProcessError:
        value = None

    return value


def find_group_by_name(api, name):
    for group in api.groups.list():
        if group.name == name:
            return group

    raise KeyError(name)


@click.group()
@click.option('--token', '-t', envvar='GITLAB_API_TOKEN',
              metavar='TOKEN')
@click.option('--url', '-u', envvar='GITLAB_URL',
              metavar='URL')
@click.pass_context
def cli(ctx, token, url):
    if token is None:
        token = git_config_value('gitlab.token')
    if token is None:
        raise click.ClickException('missing gitlab API token')

    if url is None:
        url = git_config_value('gitlab.url')
    if url is None:
        url = DEFAULT_GITLAB_URL

    ctx.obj = gitlab.Gitlab(url, token)
    ctx.obj.auth()


@cli.command()
@click.option('--group', '-g')
@click.option('--description', '-d')
@click.option('--visibility',
              type=click.Choice(['public', 'internal', 'private']))
@click.option('--enable',
              type=click.Choice(GITLAB_PROJECT_FEATURES),
              multiple=True)
@click.option('--disable',
              type=click.Choice(GITLAB_PROJECT_FEATURES),
              multiple=True)
@click.option('--import-url')
@click.option('--tag', multiple=True)
@click.argument('name')
@click.pass_context
def create(ctx, group, description, visibility, enable, disable,
           import_url, tag, name):

    if group is None and '/' in name:
        group, name = name.split('/', 1)

    data = {'name': name}

    if group is not None:
        if group.isdigit():
            data['namespace_id'] = int(group)
        else:
            data['namespace_id'] = find_group_by_name(ctx.obj, group).id

    if description is not None:
        data['description'] = description

    if visibility is not None:
        data['visibility'] = visibility

    if import_url is not None:
        data['import_url'] = import_url

    for feature in enable:
        data[GITLAB_PROJECT_FEATURES[feature]] = True
    for feature in disable:
        data[GITLAB_PROJECT_FEATURES[feature]] = False

    if tag:
        data['tag_list'] = tag

    project = ctx.obj.projects.create(data)
    print(project.web_url)


@cli.command()
@click.argument('name')
@click.pass_context
def delete(ctx, name):
    ctx.obj.projects.delete(name)


@cli.command()
def fork():
    raise click.ClickException('Not implemented')


@cli.command()
def open():
    raise click.ClickException('Not implemented')


@cli.command()
@click.option('--group', '-g')
@click.pass_context
def list(ctx, group):
    if group is not None:
        if group.isdigit():
            target = ctx.obj.groups.get(group)
        else:
            target = find_group_by_name(ctx.obj, group)
    else:
        target = ctx.obj.users.get(ctx.obj.user.id)

    for project in target.projects.list():
        print(project.name, project.web_url)


@cli.group()
def issue():
    pass


@issue.command(name='list')
def issue_list():
    pass


@issue.command(name='create')
def issue_create():
    pass


@issue.command(name='show')
def issue_show():
    pass


@cli.group()
def merge_request():
    pass


@merge_request.command(name='list')
def mr_list():
    pass


@merge_request.command(name='create')
def mr_create():
    pass


@merge_request.command(name='show')
def mr_show():
    pass


@cli.group()
def snippet():
    pass


@snippet.command(name='list')
def snippet_list():
    pass


@snippet.command(name='create')
def snippet_create():
    pass


@snippet.command(name='show')
def snippet_show():
    pass


