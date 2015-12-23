import os.path
import sys
import unittest

import six

from enstaller.new_solver.requirement import Requirement
from okonomiyaki.versions import EnpkgVersion

from simplesat.test_utils import repository_from_index
from simplesat.test_data import NUMPY_INDEX

from ..pool import Pool


V = EnpkgVersion.from_string


class TestPool(unittest.TestCase):
    def test_what_provides_tilde(self):
        # Given
        repository = repository_from_index(NUMPY_INDEX)
        requirement = Requirement._from_string("numpy ~= 1.8.1")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)

        # Then
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].full_version, "1.8.1-1")

    def test_what_provides_casing(self):
        # Given
        repository = repository_from_index(NUMPY_INDEX)
        requirement = Requirement._from_string("mkl ~= 10.2")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)
        versions = [candidate.full_version for candidate in candidates]

        # Then
        six.assertCountEqual(self, versions, ["10.2-1", "10.2-2"])

    def test_what_provides_simple(self):
        # Given
        repository = repository_from_index(NUMPY_INDEX)
        requirement = Requirement._from_string("numpy >= 1.8.0")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)
        versions = [candidate.full_version for candidate in candidates]

        # Then
        six.assertCountEqual(
            self, versions, ["1.8.0-1", "1.8.0-2", "1.8.0-3", "1.8.1-1"]
        )

    def test_what_provides_multiple(self):
        # Given
        repository = repository_from_index(NUMPY_INDEX)
        requirement = Requirement._from_string("numpy >= 1.8.0, numpy < 1.8.1")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)
        versions = [candidate.full_version for candidate in candidates]

        # Then
        six.assertCountEqual(
            self, versions, ["1.8.0-1", "1.8.0-2", "1.8.0-3"]
        )

    def test_id_to_string(self):
        # Given
        repository = repository_from_index(NUMPY_INDEX)
        requirement = Requirement._from_string("numpy >= 1.8.1")

        # When
        pool = Pool([repository])
        candidate = pool.what_provides(requirement)[0]
        package_id = pool.package_id(candidate)

        # Then
        self.assertEqual(pool.id_to_string(package_id), "+numpy-1.8.1-1")
        self.assertEqual(pool.id_to_string(-package_id), "-numpy-1.8.1-1")
