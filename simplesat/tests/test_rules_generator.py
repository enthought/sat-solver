#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import unittest

from enstaller.new_solver import Pool

from ..rules_generator import RuleType, RulesGenerator
from ..test_utils import Scenario


class TestRulesGenerator(unittest.TestCase):

    def test_prefer_installed(self):

        self.yaml = u"""
            packages:
                - A 1.0.0-1
            installed:
                - A 1.0.0-1
            marked:
                - A
            request:
                - operation: "update_all"
        """

        scenario = Scenario.from_yaml(io.StringIO(self.yaml))
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)
        rules = list(rules_generator.iter_rules())
        updates = [r for r in rules if r.reason == RuleType.job_update]

        self.assertEqual(len(updates), 1)

        update = updates[0]

        self.assertEqual(update.reason, RuleType.job_update)
        self.assertEqual(len(update.literals), 1)

        pkg_id = update.literals[0]
        package = pool._id_to_package[pkg_id]

        self.assertEqual(package.repository_info.name, "installed")
