import unittest

import six

from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints import PrettyPackageStringParser, Requirement
from simplesat.repository import Repository
from simplesat.request import Request

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

    def test_what_provides_caret(self):
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

    def test_transform(self):
        # Given
        repository = Repository(self.packages_from_definition(
            "numpy 1.8.1-1; depends (MKL == 10.3-1)"))
        request = Request()
        request.modifiers.allow_newer.add('MKL')

        # When
        pool = Pool([repository], modifiers=request.modifiers)
        numpy_181 = pool.name_to_packages('numpy')[0]
        result = numpy_181.install_requires
        expected = (('MKL', ((">= 10.3-1",),)),)

        # Then
        self.assertEqual(result, expected)

    def test_reset_packages(self):
        # When
        pool = Pool()
        repository = Repository(self.packages_from_definition(
            "numpy 1.8.1-1; depends (MKL == 10.3-1)"))

        # Then
        self.assertEqual((), pool.package_ids)

        # When
        pool.add_repository(repository)

        # Then
        self.assertEqual((1,), pool.package_ids)

        # When
        package = pool.id_to_package(1)
        pool._reset_packages()

        # Then
        with self.assertRaises(KeyError):
            pool._id_to_package_[1]
        with self.assertRaises(KeyError):
            pool._package_to_id_[package]
        self.assertEqual(pool._packages_by_name_[package.name], [])

    def test_recompute(self):
        # When
        pool = Pool()
        self.assertEqual((), pool.package_ids)
        repository = Repository(self.packages_from_definition(
            "numpy 1.8.1-1; depends (MKL == 10.3-1)"))

        # Then
        pool.add_repository(repository)
        self.assertEqual((1,), pool.package_ids)

        # When
        package = pool.id_to_package(1)
        pool._reset_packages()

        # Then
        self.assertEqual(package, pool.id_to_package(1))

        # When / Then
        pool._reset_packages()
        self.assertEqual(1, pool.package_id(package))

        # When / Then
        pool._reset_packages()
        self.assertEqual(pool.id_to_string(1), "+numpy-1.8.1-1")

        # When / Then
        pool._reset_packages()
        self.assertEqual((package,), pool.name_to_packages('numpy'))
