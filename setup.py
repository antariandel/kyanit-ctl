import os

import setuptools

try:
    from kyanit_buildtools import versioning
except ImportError:
    raise ImportError("kyanit_buildtools is required for building, install it first")

PACKAGE_FOLDER = "kyanitctl"


version = versioning.GitReleaseStatus().head

with open(os.path.join(PACKAGE_FOLDER, "_version.py"), "w") as f:
    f.write(f'__version__ = "{version}"')

setuptools.setup(version=version)
