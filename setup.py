import os
import re
import subprocess
import setuptools


def describe_head():
    """
    Return version string of current commit.
    
    If the current commit is version-tagged, and working tree is clean, return tagged version as-is,
    otherwise append .postN.dev0 to the version, where N is the number of commits since the latest
    version. N is incremented by 1, if the working tree is not clean.

    Returned value does not contain the "v" version prefix.

    `Exception('working tree broken')` is raised if the working tree is broken.
    """

    try:
        git_describe = subprocess.check_output(
            'git describe --tags --match "v*" --dirty --broken').decode().strip()[1:]
    except subprocess.CalledProcessError:
        return '0.0.0.dev0'
    if '-broken' in git_describe:
        raise Exception('working tree broken')
    match = re.match(r'([0-9]+\.[0-9]+\.[0-9]+)(\-([0-9+]))?', git_describe)
    if match.group(2) is None:
        # HEAD on tagged commit, append .post1.dev0, if working tree is not clean
        return '{}{}'.format(match.group(1), '.post1.dev0' if '-dirty' in git_describe else '')
    else:
        # HEAD not on tagged commit, append .postN.dev0, incrementing N if working tree is dirty
        return '{}.post{}.dev0'.format(match.group(1),
                                       int(match.group(3)) + 1 if '-dirty' in git_describe else 0)


# write version to kyanitctl._version
with open(os.path.join('kyanitctl', '_version.py'), 'w') as file:
    file.write('__version__ = \'{}\''.format(describe_head()))

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='kyanitctl',
    version=describe_head(),
    author='Zsolt Nagy',
    author_email='zsolt@kyanit.eu',
    description='Command-line utility for Kyanit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kyanit-project/kyanitctl',
    packages=setuptools.find_packages(),
    install_requires=[
        'kyanitapi'
    ],
    entry_points={
        'console_scripts': ['kyanitctl=kyanitctl:command_line'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
    ],
    license='GPLv3',
    python_requires='>=3.6',
)
