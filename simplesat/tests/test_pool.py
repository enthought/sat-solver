import unittest

import six

from okonomiyaki.platforms import PythonImplementation
from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import PrettyPackageStringParser, Requirement
from simplesat.repository import Repository

from ..pool import Pool


V = EnpkgVersion.from_string


NUMPY_PACKAGES = u"""\
mkl 10.2-1
mkl 10.2-2
mkl 10.3-1
numpy 1.4.0-1
numpy 1.4.0-2
numpy 1.4.0-4; depends (MKL ^= 10.2)
numpy 1.4.0-6; depends (MKL == 10.2-2)
numpy 1.4.0-7; depends (MKL == 10.2-2)
numpy 1.4.0-8; depends (MKL == 10.2-2)
numpy 1.4.0-9; depends (MKL == 10.2-2)
numpy 1.5.1-1; depends (MKL == 10.3-1)
numpy 1.5.1-2; depends (MKL == 10.3-1)
numpy 1.6.0-0
numpy 1.6.0-1; depends (MKL == 10.3-1)
numpy 1.6.0-2; depends (MKL == 10.3-1)
numpy 1.6.0-3; depends (MKL == 10.3-1)
numpy 1.6.0-4; depends (MKL == 10.3-1)
numpy 1.6.0-5; depends (MKL == 10.3-1)
numpy 1.6.0b2-1; depends (MKL == 10.3-1)
numpy 1.6.1-1; depends (MKL == 10.3-1)
numpy 1.6.1-2; depends (MKL == 10.3-1)
numpy 1.6.1-3; depends (MKL == 10.3-1)
numpy 1.6.1-5; depends (MKL == 10.3-1)
numpy 1.7.1-1; depends (MKL == 10.3-1)
numpy 1.7.1-2; depends (MKL == 10.3-1)
numpy 1.7.1-3; depends (MKL == 10.3-1)
numpy 1.8.0-1; depends (MKL == 10.3-1)
numpy 1.8.0-2; depends (MKL == 10.3-1)
numpy 1.8.0-3; depends (MKL == 10.3-1)
numpy 1.8.1-1; depends (MKL == 10.3-1)
"""


class TestPool(unittest.TestCase):
    def packages_from_definition(self, packages_definition):
        parser = PrettyPackageStringParser(EnpkgVersion.from_string)

        return [
            parser.parse_to_package(line)
            for line in packages_definition.splitlines()
        ]

    def test_what_provides_tilde(self):
        # Given
        repository = Repository(self.packages_from_definition(NUMPY_PACKAGES))
        requirement = Requirement._from_string("numpy ^= 1.8.1")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)

        # Then
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].version, V("1.8.1-1"))

    def test_what_provides_casing(self):
        # Given
        repository = Repository(self.packages_from_definition(NUMPY_PACKAGES))
        requirement = Requirement._from_string("mkl ^= 10.2")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)
        versions = [str(candidate.version) for candidate in candidates]

        # Then
        six.assertCountEqual(self, versions, ["10.2-1", "10.2-2"])

    def test_what_provides_simple(self):
        # Given
        repository = Repository(self.packages_from_definition(NUMPY_PACKAGES))
        requirement = Requirement._from_string("numpy >= 1.8.0")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)
        versions = [str(candidate.version) for candidate in candidates]

        # Then
        six.assertCountEqual(
            self, versions, ["1.8.0-1", "1.8.0-2", "1.8.0-3", "1.8.1-1"]
        )

    def test_what_provides_multiple(self):
        # Given
        repository = Repository(self.packages_from_definition(NUMPY_PACKAGES))
        requirement = Requirement._from_string("numpy >= 1.8.0, numpy < 1.8.1")

        # When
        pool = Pool([repository])
        candidates = pool.what_provides(requirement)
        versions = [str(candidate.version) for candidate in candidates]

        # Then
        six.assertCountEqual(
            self, versions, ["1.8.0-1", "1.8.0-2", "1.8.0-3"]
        )

    def test_id_to_string(self):
        # Given
        repository = Repository(self.packages_from_definition(NUMPY_PACKAGES))
        requirement = Requirement._from_string("numpy >= 1.8.1")

        # When
        pool = Pool([repository])
        candidate = pool.what_provides(requirement)[0]
        package_id = pool.package_id(candidate)

        # Then
        self.assertEqual(pool.id_to_string(package_id), "+numpy-1.8.1-1")
        self.assertEqual(pool.id_to_string(-package_id), "-numpy-1.8.1-1")
