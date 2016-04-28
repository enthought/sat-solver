from attr import attr, attributes, Factory
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


@attributes
class Request(object):
    """
    A proposed change to the state of the installed repository.

    The Request is built up from :class:`Requirement` objects and
    ad-hoc package constraint modifiers.

    Parameters
    ----------
    modifiers : ConstraintModifiers, optional
        The contraint modifiers are used to relax constraints when deciding
        on which packages meet a requirement.


    >>> from simplesat.request import Request
    >>> from simplesat.constraints import Requirement
    >>> request = Request()
    >>> recent_mkl = Requirement.from_string('MKL >= 11.0')
    >>> request.install(recent_mkl)
    >>> request.jobs
    [_Job(requirement=Requirement('MKL >= 11.0-0'), kind=<JobType.install: 1>)]
    >>> request.modifiers
    ConstraintModifiers(allow_newer=set(), allow_any=set(), allow_older=set())
    >>> request.allow_newer('MKL')
    >>> request.modifiers.asdict()
    {'allow_older': [], 'allow_any': ['MKL'], 'allow_newer': []}
    """

    modifiers = attr(default=Factory(ConstraintModifiers))
    jobs = attr(default=Factory(list))

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
