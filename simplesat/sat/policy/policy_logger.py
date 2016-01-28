# -*- coding: utf-8 -*-

from collections import Counter

from .policy import IPolicy


class PolicyLogger(IPolicy):

    def __init__(self, policy, extra_args=None, extra_kwargs=None):
        self._policy = policy
        self._log_pool = policy._pool
        self._log_installed = policy._installed_ids.copy()
        self._log_preferred = getattr(policy, '_preferred_ids', set()).copy()
        self._log_extra_args = extra_args
        self._log_extra_kwargs = extra_kwargs
        self._log_required = []
        self._log_suggestions = []
        self._log_assignment_changes = []

    def get_next_package_id(self, assignments, clauses):
        self._log_assignment_changes.append(assignments.get_changelog())
        pkg_id = self._policy.get_next_package_id(assignments, clauses)
        self._log_suggestions.append(pkg_id)
        assignments.consume_changelog()
        return pkg_id

    def add_requirements(self, package_ids):
        self._log_required.extend(package_ids)
        self._log_preferred.difference_update(package_ids)
        self._log_installed.difference_update(package_ids)
        self._policy.add_requirements(package_ids)

    def _log_histogram(self, pkg_ids=None):
        if pkg_ids is None:
            pkg_ids = map(abs, self._log_suggestions)
        c = Counter(pkg_ids)
        lines = (
            "{:>25} {}".format(self._log_pretty_pkg_id(k), v)
            for k, v in c.most_common()
        )
        pretty = '\n'.join(lines)
        return c, pretty

    def _log_pretty_pkg_id(self, pkg_id):
        package = self._log_pool._id_to_package[pkg_id]
        name_ver = '{} {}'.format(package.name, package.version)
        fill = '.' if pkg_id % 2 else ''
        repo = package.repository_info.name
        return "{:{fill}<30} {:3} {}".format(name_ver, pkg_id, repo, fill=fill)

    def _log_report(self, ids=None):

        def pkg_name(pkg_id):
            return pkg_key(pkg_id)[0]

        def pkg_key(pkg_id):
            pkg = self._log_pool._id_to_package[pkg_id]
            return pkg.name, pkg.version

        if ids is None:
            ids = map(abs, self._log_suggestions)
        report = []
        changes = []
        if self._log_assignment_changes:
            for pkg, change in self._log_assignment_changes[0].items():
                name = self._log_pretty_pkg_id(pkg)
                if change[1] is not None:
                    changes.append("{} : {}".format(name, change[1]))
            report.append('\n'.join(changes))

        required = set(self._log_required)
        preferred = set(self._log_preferred)
        installed = set(self._log_installed)
        for (i, sugg) in enumerate(ids):
            pretty = self._log_pretty_pkg_id(sugg)
            R = 'R' if sugg in required else ' '
            P = 'P' if sugg in preferred else ' '
            I = 'I' if sugg in installed else ' '
            changes = []
            try:
                items = self._log_assignment_changes[i + 1].items()
                for pkg, change in sorted(items, key=lambda p: pkg_key(p[0])):
                    if pkg_name(pkg) != pkg_name(sugg):
                        _pretty = self._log_pretty_pkg_id(pkg)
                        fro, to = map(str, change)
                        msg = "{:10} - {:10} : {}"
                        changes.append(msg.format(fro, to, _pretty))
                if changes:
                    changes = '\n\t\t'.join([''] + changes)
                else:
                    changes = ""
            except IndexError:
                changes = ""
            msg = "{:>4} {}{}{} - {}{}"
            report.append(msg.format(i, R, P, I, pretty, changes))
        return '\n'.join(report)
