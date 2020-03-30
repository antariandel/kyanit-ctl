import setuptools

import kyanitctl

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='kyanitctl',
    version=kyanitctl.__version__,
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
    python_requires='>=3.6',
)
