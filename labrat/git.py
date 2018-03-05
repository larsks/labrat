import collections
import logging
import subprocess
from urllib import parse as urlparse

LOG = logging.getLogger(__name__)

GitRemote = collections.namedtuple(
    'GitRemote',
    ['scheme', 'user', 'host', 'port', 'path'])


def git_config_value(key):
    try:
        value = subprocess.check_output(
            ['git', 'config', '--get', key]
        ).strip()
    except subprocess.CalledProcessError:
        value = None

    return value


def git_get_origin():
    tracking = subprocess.check_output(
        ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}']
    ).strip().decode('utf8')

    LOG.debug('got tracking branch: %s', tracking)

    remote, branch = tracking.split('/', 1)
    remote_url = subprocess.check_output(
        ['git', 'ls-remote', '--get-url', remote]
    ).strip().decode('utf8')

    LOG.debug('got remote url %s for remote %s, branch %s',
              remote_url, remote, branch)

    if '://' in remote_url:
        scheme, netloc, path, query, fragment = urlparse.urlsplit(remote_url)
        path = path[1:]
    elif ':' in remote_url:
        scheme = 'ssh'
        netloc, path = remote_url.split(':', 1)
    else:
        return None

    if path.endswith('.git'):
        path = path[:-4]

    LOG.debug('got netloc = %s, path = %s', netloc, path)

    if '@' in netloc:
        user, host = netloc.split('@', 1)
    else:
        user, host = None, netloc

    if ':' in host:
        host, port = host.split(':', 1)
    else:
        host, port = host, None

    return GitRemote(scheme, user, host, port, path)
