# -*- coding: utf-8 -*-

import io
import unittest

from simplesat.errors import NoPackageFound
from simplesat.constraints.requirement_transformation import (
    TransformedRequirement
)

from ..pool import Pool
from ..rules_generator import RuleType, RulesGenerator
from ..test_utils import Scenario


class TestRulesGenerator(unittest.TestCase):

    def test_prefer_installed(self):

        # Given
        yaml = u"""
            packages:
                - A 1.0.0-1
            installed:
                - A 1.0.0-1
            marked:
                - A
            request:
                - operation: "update_all"
        """
        scenario = Scenario.from_yaml(io.StringIO(yaml))

        # When
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)
        rules = list(rules_generator.iter_rules())

        # Then
        self.assertEqual(len(rules), 2)

        # Given/When
        update = rules[1]

        # Then
        self.assertEqual(update.reason, RuleType.job_update)
        self.assertEqual(len(update.literals), 1)

        # Given
        installed_repo_package = next(iter(scenario.installed_repository))

        # When
        pkg_id = update.literals[0]
        package = pool._id_to_package[pkg_id]

        # Then
        self.assertIs(package, installed_repo_package)

    def test_conflicts(self):
        # Given
        yaml = u"""
            packages:
              - quark 1.0.1-2
              - atom 1.0.0-1; depends (quark > 1.0); conflicts (gdata ^= 1.0.0)
              - atom 1.0.1-1; depends (quark)
              - gdata 1.0.0-1; conflicts (atom >= 1.0.1)

            request:
              - operation: "install"
                requirement: "atom"
              - operation: "install"
                requirement: "gdata"
        """
        scenario = Scenario.from_yaml(io.StringIO(yaml))

        # When
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)
        rules = list(rules_generator.iter_rules())

        # Then
        self.assertEqual(len(rules), 7)

        # Given/When
        conflict = rules[2]
        r_literals = (-3, -1)

        # Then
        self.assertEqual(conflict.reason, RuleType.package_conflicts)
        self.assertEqual(conflict.literals, r_literals)

        # Given/When
        conflict = rules[5]
        r_literals = (-3, -2)

        # Then
        self.assertEqual(conflict.reason, RuleType.package_conflicts)
        self.assertEqual(conflict.literals, r_literals)

    def test_missing_dependencies_package(self):
        # Given
        yaml = u"""
            packages:
              - atom 1.0.0-1; depends (quark > 1.0); conflicts (gdata ^= 1.0.0)
              - gdata 1.0.0-1; conflicts (atom >= 1.0.1)

            request:
              - operation: "install"
                requirement: "atom"
        """
        scenario = Scenario.from_yaml(io.StringIO(yaml))

        # When
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)

        # Then
        with self.assertRaises(NoPackageFound):
            list(rules_generator.iter_rules())

    def test_missing_conflicts_package(self):
        # Given
        yaml = u"""
            packages:
              - quark 1.0.0-1
              - atom 1.0.0-1; depends (quark > 1.0); conflicts (gdata ^= 1.0.0)

            request:
              - operation: "install"
                requirement: "atom"
        """
        scenario = Scenario.from_yaml(io.StringIO(yaml))

        # When
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)

        # Then
        with self.assertRaises(NoPackageFound):
            list(rules_generator.iter_rules())

    def test_allow_newer_transformation(self):
        # Given
        yaml = u"""
            packages:
              - atom 1.0.1-1; depends (quark > 1.0, quark < 2.0)
              - quark 1.1.0-1
              - quark 2.1.0-1

            request:
              - operation: "install"
                requirement: "atom"
        """
        scenario = Scenario.from_yaml(io.StringIO(yaml))
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}

        # When
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)
        rule = next(rule for rule in rules_generator.iter_rules()
                    if rule.reason == RuleType.package_requires)

        # Then
        expected = (-1, 2)
        result = rule.literals
        self.assertEqual(expected, result)

        # When
        original_rule = rule
        scenario.request.allow_newer('quark')
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)
        rule = next(rule for rule in rules_generator.iter_rules()
                    if rule.reason == RuleType.package_requires)
        requirement = next(req for req in rule._requirements
                           if req.name == 'quark')

        # Then
        expected = (-1, 2, 3)
        result = rule.literals
        self.assertEqual(expected, result)

        self.assertIsInstance(requirement, TransformedRequirement)

        expected = requirement._original_requirement
        result = next(req for req in original_rule._requirements
                      if req.name == 'quark')
        self.assertEqual(expected, result)

    def test_adhoc_constraint(self):
        # Given
        yaml = u"""
            packages:
              - quark 1.1.0-1
              - quark 1.2.0-1
              - quark 2.1.0-1
              - quark 3.1.0-1

            request:
              - operation: "constrain"
                requirement: "quark > 2.0"
        """
        scenario = Scenario.from_yaml(io.StringIO(yaml))
        repos = list(scenario.remote_repositories)
        repos.append(scenario.installed_repository)
        pool = Pool(repos)
        installed_map = {
            pool.package_id(p): p for p in scenario.installed_repository}

        # When
        rules_generator = RulesGenerator(pool, scenario.request, installed_map)
        rules = tuple(rules_generator.iter_rules())

        # Then
        self.assertEqual(len(rules), 2)
        for rule, expected in zip(rules, ((-1,), (-2,))):
            result = rule.literals
            self.assertEqual(expected, result)
