from attr import attr, attributes
from attr.validators import instance_of
from enum import Enum

from .constraints import Requirement, ConstraintModifiers


class JobType(Enum):
    install = 1
    remove = 2
    update = 3


@attributes
class _Job(object):
    requirement = attr(validator=instance_of(Requirement))
    kind = attr(validator=instance_of(JobType))


class Request(object):
    def __init__(self, modifiers=None):
        self.jobs = []
        self.modifiers = modifiers or ConstraintModifiers()

    def install(self, requirement):
        self._add_job(requirement, JobType.install)

    def remove(self, requirement):
        self._add_job(requirement, JobType.remove)

    def update(self, requirement):
        self._add_job(requirement, JobType.update)

    def allow_newer(self, package_name):
        self.modifiers.allow_newer.add(package_name)

    def allow_any(self, package_name):
        self.modifiers.allow_any.add(package_name)

    def allow_older(self, package_name):
        self.modifiers.allow_older.add(package_name)

    def _add_job(self, requirement, job_type):
        self.jobs.append(_Job(requirement, job_type))
