import re
import collections
import subprocess

from io import StringIO

import semver


def get_commit_history(until_rev=None):
    """
    Return an OrderedDict of the git log, where the key is the revision number. First key is the
    newest commit.

    If `until_rev` is not `None`, return log up to the revision that matches `until_rev`.
    """

    if until_rev is not None:
        GIT_CMD = 'git log --no-decorate --log-size "{}"..'.format(until_rev)
    else:
        GIT_CMD = 'git log --no-decorate --log-size'

    git_process = subprocess.Popen(GIT_CMD, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    git_output = git_process.communicate()[0]
    git_output = StringIO(git_output.decode())

    commits = collections.OrderedDict()
    while True:
        line = git_output.readline()
        if not line:
            break
        revision = re.match(r'commit ([0-9|a-f]+)', line).group(1)
        log_size = int(re.match(r'log size (\d+)', git_output.readline()).group(1))
        commit_info = git_output.read(log_size)
        commits[revision] = commit_info
        git_output.readline()  # read empty line after commit
    return commits  # newest first


def get_latest_version():
    GIT_CMD = 'git describe --tags --abbrev=0'
    try:
        last_tag = subprocess.check_output(GIT_CMD, stderr=subprocess.DEVNULL).decode().strip()
    except subprocess.CalledProcessError:
        # can not describe (probably no tags yet)
        return None
    if not last_tag.startswith('v'):
        raise RuntimeError('last git tag is not a version tag')
    version = last_tag[1:]
    try:
        semver.parse(version)
    except ValueError:
        raise RuntimeError('last version tag is not valid SemVer')
    return version


def get_commit_oneline(commit):
    commit = StringIO(commit)
    while True:
        for i in range(3):
            commit.readline()  # discard author and date
        line = commit.readline().strip()
        return line.partition(':')[2] if ':' in line else line


def get_commit_types(commits, include=[]):
    """
    Return an OrderedDict of commit types extracted from `commits`, where the key is the revision
    number. First key is the newest commit.

    If `include` is not empty, only commits with the types listed in `include` will be returned.
    """

    commits_out = collections.OrderedDict()
    for revision in commits:
        commit_info = StringIO(commits[revision])
        for i in range(3):
            commit_info.readline()  # discard author and date
        commit_type = re.match(r'\s+([a-z]+)[(|!|:]', commit_info.readline()).group(1)
        if include and commit_type not in include:
            continue
        while True:
            line = commit_info.readline()
            if not line:
                break
            if 'BREAKING CHANGE' in line or 'BREAKING-CHANGE' in line:
                commit_type = '{}!'.format(commit_type)
                break
        commits_out[revision] = commit_type
    return commits_out  # newest first


def bump_version_from_hist(start_version, commit_types):
    """
    Return a new SemVer starting from `start_version` based on the `commit_types`.

    Starting at `start_version`, bump a major version if there's at least one breaking change in
    the commit type history, and return it. Otherwise bump a minor version if there's at least one
    feature type change in the history, and return it. Otherwise bump a patch version, if there's at
    least one fix type change in the history, and return it. Return `start_version` if none of the
    previous applies.
    """
    
    version = semver.parse_version_info(start_version)
    commit_types = list(commit_types.values())
    for commit_type in commit_types:
        if '!' in commit_type:
            if version.major == 0:
                return str(version.bump_minor())
            else:
                return str(version.bump_major())
    if 'feat' in commit_types:
        return str(version.bump_minor())
    if 'fix' in commit_types:
        return str(version.bump_patch())
    return start_version


def gen_version():
    latest_version = get_latest_version()
    if not latest_version:
        latest_version = '0.0.0'
    commits = get_commit_history(until_rev=latest_version)
    commit_types = get_commit_types(commits)
    new_version = bump_version_from_hist(latest_version, commit_types)

    if new_version == latest_version:
        print('version unchanged: {}'.format(latest_version))
        return latest_version

    print('version bump needed: {} -> {}'.format(latest_version, new_version), end='\n\n')
    print('features:', end='\n\n')
    for rev in commit_types:
        if commit_types[rev].startswith('feat'):
            print('{} : {}'.format(rev[:8], get_commit_oneline(commits[rev])))
    print('\nfixes:', end='\n\n')
    for rev in commit_types:
        if commit_types[rev].startswith('fix'):
            print('{} : {}'.format(rev[:8], get_commit_oneline(commits[rev])))
    
    return new_version


if __name__ == '__main__':
    gen_version()
