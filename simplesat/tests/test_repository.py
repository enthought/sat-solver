import textwrap
import unittest

from okonomiyaki.platforms import PythonImplementation
from okonomiyaki.versions import EnpkgVersion

from enstaller.package import PackageMetadata, RemotePackageMetadata
from enstaller.repository_info import BroodRepositoryInfo, FSRepositoryInfo

from simplesat.constraints import PrettyPackageStringParser
from simplesat.errors import NoPackageFound
from simplesat.repository import Repository


V = EnpkgVersion.from_string


class TestRepository(unittest.TestCase):
    def packages_from_definition(self, packages_definition):
        python_implementation = PythonImplementation.from_running_python()
        parser = PrettyPackageStringParser(EnpkgVersion.from_string)

        return [
            parser.parse_to_package(line, python_implementation)
            for line in packages_definition.splitlines()
        ]

    def test_simple(self):
        # Given
        packages_definition = textwrap.dedent("""\
        dummy 1.0.1-1
        dummy_with_appinst 1.0.0-1
        dummy_with_entry_points 1.0.0-1
        dummy_with_proxy 1.3.40-3
        dummy_with_proxy_scripts 1.0.0-1
        dummy_with_proxy_softlink 1.0.0-1
        nose 1.2.1-1
        nose 1.3.0-1
        nose 1.3.0-2\
        """)
        packages = self.packages_from_definition(packages_definition)

        # When
        repository = Repository()

        # Then
        self.assertEqual(len(repository), 0)

        # When
        repository = Repository(packages)

        # Then
        self.assertEqual(len(repository), len(packages))
        self.assertEqual(list(repository), packages)

        # When
        repository = Repository(reversed(packages))

        # Then
        self.assertEqual(len(repository), len(packages))
        self.assertEqual(list(repository), packages)

    def test_find_package(self):
        # Given
        packages_definition = textwrap.dedent("""\
        dummy 1.0.1-1
        dummy_with_appinst 1.0.0-1
        dummy_with_entry_points 1.0.0-1
        dummy_with_proxy 1.3.40-3
        dummy_with_proxy_scripts 1.0.0-1
        dummy_with_proxy_softlink 1.0.0-1
        nose 1.2.1-1
        nose 1.3.0-1
        nose 1.3.0-2\
        """)
        packages = self.packages_from_definition(packages_definition)
        repository = Repository(packages)

        # When
        package = repository.find_package("nose", V("1.3.0-1"))

        # Then
        self.assertEqual(package.key, "nose-1.3.0-1.egg")

    def test_find_unavailable_package(self):
        # Given
        packages_definition = textwrap.dedent("""\
        dummy 1.0.1-1
        dummy_with_appinst 1.0.0-1
        dummy_with_entry_points 1.0.0-1
        dummy_with_proxy 1.3.40-3
        dummy_with_proxy_scripts 1.0.0-1
        dummy_with_proxy_softlink 1.0.0-1
        nose 1.2.1-1
        nose 1.3.0-1
        nose 1.3.0-2\
        """)
        packages = self.packages_from_definition(packages_definition)
        repository = Repository(packages)

        # When/Then
        with self.assertRaises(NoPackageFound):
            repository.find_package("nose", V("1.4.0-1"))

        with self.assertRaises(NoPackageFound):
            repository.find_package("nono", V("1.4.0-1"))

    def test_find_packages(self):
        # Given
        packages_definition = textwrap.dedent("""\
        dummy 1.0.1-1
        dummy_with_appinst 1.0.0-1
        dummy_with_entry_points 1.0.0-1
        dummy_with_proxy 1.3.40-3
        dummy_with_proxy_scripts 1.0.0-1
        dummy_with_proxy_softlink 1.0.0-1
        nose 1.3.0-1
        nose 1.2.1-1
        nose 1.3.0-2\
        """)
        packages = self.packages_from_definition(packages_definition)
        repository = Repository(packages)

        r_versions = [V("1.2.1-1"), V("1.3.0-1"), V("1.3.0-2")]

        # When
        packages = repository.find_packages("nose")

        # Then
        self.assertEqual(len(packages), 3)

        # When
        # Ensure find_packages returns a copy of the metadata
        packages[:] = []
        packages = repository.find_packages("nose")

        # Then
        self.assertEqual(len(packages), 3)
        self.assertEqual([p.version for p in packages], r_versions)

        # When
        packages = repository.find_packages("non_existing_package")

        # Then
        self.assertEqual(len(packages), 0)
