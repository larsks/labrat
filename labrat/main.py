import click
import gitlab
import json
import logging
import os
import webbrowser

from labrat import git

LOG = logging.getLogger(__name__)

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


class LabratOptions(object):
    force = False
    loglevel = logging.WARNING

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise AttributeError(k)

    def __setattr__(self, k, v):
        if not hasattr(self, k):
            raise AttributeError(k)

        super().__setattr__(k, v)


class Labrat(object):
    def __init__(self, url=None, token=None, **options):
        self.options = LabratOptions(**options)

        if url is None:
            url = git.git_config_value('gitlab.url')
        if url is None:
            url = DEFAULT_GITLAB_URL

        if token is None:
            token = git.git_config_value('gitlab.token')
        if token is None:
            raise click.ClickException('missing gitlab API token')

        LOG.info('using gitlab url: %s', url)
        self.api = gitlab.Gitlab(url, token)
        self.api.auth()

    def find_group_by_name(self, name):
        for group in self.api.groups.list():
            if group.name == name:
                return group

        raise KeyError(name)

    def get_project_from_git(self):
        origin = git.git_get_origin()

        try:
            project = self.api.projects.get(origin.path)
            return project
        except gitlab.exceptions.GitlabGetError:
            raise click.ClickException(
                'unable to locate project named %s' % origin.path)


@click.group()
@click.option('--token', '-t', envvar='GITLAB_TOKEN',
              metavar='TOKEN')
@click.option('--url', '-u', envvar='GITLAB_URL',
              metavar='URL')
@click.option('--debug', 'loglevel', flag_value='DEBUG')
@click.option('--verbose', 'loglevel', flag_value='INFO')
@click.option('--quiet', 'loglevel', flag_value='WARNING', default=True)
@click.option('--force', '-f', is_flag=True, default=False)
@click.pass_context
def cli(ctx, token, url, loglevel, force):
    logging.basicConfig(level=loglevel)
    ctx.obj = Labrat(url, token,
                     loglevel=loglevel,
                     force=force)


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
@click.argument('name', default=None, required=False)
@click.pass_context
def create(ctx, group, description, visibility, enable, disable,
           import_url, tag, name):
    lab = ctx.obj

    if name is None:
        name = os.path.basename(git.get_toplevel())

    if group is None and '/' in name:
        group, name = name.split('/', 1)

    data = {'name': name}

    if group is not None:
        if group.isdigit():
            data['namespace_id'] = int(group)
        else:
            data['namespace_id'] = lab.find_group_by_name(group).id

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

    LOG.debug('create %s', data)
    project = lab.api.projects.create(data)
    print(project.web_url)


@cli.command()
@click.argument('name')
@click.pass_context
def delete(ctx, name):
    lab = ctx.obj
    lab.api.projects.delete(name)


@cli.command()
@click.option('--namespace', '-n')
@click.option('--use-ssh-url', 'schema', flag_value='ssh', default=True)
@click.option('--use-http-url', 'schema', flag_value='http')
@click.pass_context
def fork(ctx, namespace, schema):
    lab = ctx.obj

    if namespace is None:
        namespace = lab.api.user.username

    project = lab.get_project_from_git()

    LOG.info('forking project %s to %s', project.name, namespace)
    fork = project.forks.create(dict(namespace=namespace))

    if schema == 'ssh':
        url = fork.ssh_url_to_repo
    elif schema == 'http':
        url = fork.http_url_to_repo
    else:
        raise click.ClickException('unknown schema: %s', schema)

    remote_name = lab.api.user.username
    if git.git_remote_exists(remote_name):
        if not lab.options.force:
            raise click.ClickException('A remote named "%s" already '
                                       'exists' % remote_name)

        LOG.info('updating remote %s', remote_name)
        git.git_remote_set_url(remote_name, url)
    else:
        LOG.info('creating remote %s', remote_name)
        git.git_remote_create(remote_name, url)

    print(fork.web_url)


@cli.command()
@click.pass_context
def info(ctx):
    lab = ctx.obj
    project = lab.get_project_from_git()
    data = {k: getattr(project, k)
            for k in ['name', 'id', 'description', 'web_url',
                      'ssh_url_to_repo', 'http_url_to_repo',
                      'last_activity_at']
            if hasattr(project, k)}
    print(json.dumps(data, indent=2, sort_keys=True))


@cli.command()
@click.pass_context
def open(ctx):
    lab = ctx.obj

    project = lab.get_project_from_git()
    webbrowser.open(project.web_url)


@cli.command()
@click.option('--group', '-g')
@click.pass_context
def list(ctx, group):
    lab = ctx.obj

    if group is not None:
        if group.isdigit():
            target = lab.api.groups.get(group)
        else:
            target = lab.find_group_by_name(group)
    else:
        target = lab.api.users.get(lab.api.user.id)

    for project in target.projects.list():
        print(project.name, project.web_url)


@cli.group()
def issue():
    pass


@issue.command(name='list')
def issue_list():
    raise click.ClickException('Not implemented')


@issue.command(name='create')
def issue_create():
    raise click.ClickException('Not implemented')


@issue.command(name='show')
def issue_show():
    raise click.ClickException('Not implemented')


@cli.group(name='merge-request')
def merge_request():
    pass


@merge_request.command(name='list')
def mr_list():
    raise click.ClickException('Not implemented')


@merge_request.command(name='create')
def mr_create():
    raise click.ClickException('Not implemented')


@merge_request.command(name='show')
def mr_show():
    raise click.ClickException('Not implemented')


@cli.group()
def snippet():
    raise click.ClickException('Not implemented')


@snippet.command(name='list')
def snippet_list():
    raise click.ClickException('Not implemented')


@snippet.command(name='create')
def snippet_create():
    raise click.ClickException('Not implemented')


@snippet.command(name='show')
def snippet_show():
    raise click.ClickException('Not implemented')


@cli.command(name='get-origin')
def get_origin():
    print(json.dumps(git.git_get_origin()))


@cli.group()
def branch():
    pass


@branch.command(name='protect')
@click.argument('branch', required=False)
@click.pass_context
def branch_protect(ctx, branch):
    lab = ctx.obj
    project = lab.get_project_from_git()

    if branch is None:
        branch = git.git_get_upstream()
        remote, branch = branch.split('/', 1)

    LOG.debug('protecting branch %s', branch)

    try:
        project.protectedbranches.create(dict(name=branch))
        print(f'protected branch {branch}')
    except gitlab.exceptions.GitlabCreateError as err:
        if err.response_code == 409:
            print(f'Branch {branch} is already protected')
        else:
            raise


@branch.command(name='unprotect')
@click.argument('branch', required=False)
@click.pass_context
def branch_unprotect(ctx, branch):
    lab = ctx.obj
    project = lab.get_project_from_git()

    if branch is None:
        branch = git.git_get_upstream()
        remote, branch = branch.split('/', 1)

    LOG.debug('unprotecting branch %s', branch)

    try:
        project.protectedbranches.delete(id=branch)
        print(f'unprotected branch {branch}')
    except gitlab.exceptions.GitlabCreateError as err:
        if err.response_code == 404:
            print(f'No such branch named {branch}')
        else:
            raise
