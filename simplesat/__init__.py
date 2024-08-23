from __future__ import absolute_import

from .constraints import Requirement, InstallRequirement
from .package import PackageMetadata, RepositoryPackageMetadata, RepositoryInfo
from .pool import Pool
from .repository import Repository
from .request import JobType, Request

try:  # pragma: no cover
    from ._version import (
        version as __version__, version_info as __version_info__,
        is_released as __is_released__, git_revision as __git_revision__,
    )
except ImportError:  # pragma: no cover
    __is_released__ = False
    __version__ = __git_revision__ = "unknown"
    __version_info__ = (0, 0, 0, "unknown", 0)


__all__ = [
    'Requirement',
    'InstallRequirement',
    'PackageMetadata',
    'RepositoryPackageMetadata',
    'RepositoryInfo',
    'Pool',
    'Repository',
    'JobType',
    'Request',
    '__is_released__',
    '__version__',
    '__version_info__']
