import sys
import unittest

from okonomiyaki.platforms import PythonImplementation
from okonomiyaki.versions import EnpkgVersion

from simplesat.constraints.package_parser import (
    PrettyPackageStringParser, package_to_pretty_string
)
from simplesat.package import PackageMetadata


RUNNING_PYTHON = PythonImplementation(
    "cp", sys.version_info[0], sys.version_info[1]
)

V = EnpkgVersion.from_string


class TestPrettyPackageStringParser(unittest.TestCase):
    def test_invalid_formats(self):
        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = ""
        r_message = "Invalid preamble: "

        # Then
        with self.assertRaisesRegexp(ValueError, r_message):
            parse(package_string)

        # Given
        package_string = "numpy"
        r_message = "Invalid preamble: 'numpy'"

        # Then
        with self.assertRaisesRegexp(ValueError, r_message):
            parse(package_string)

        # Given
        package_string = "numpy1.8.0-1"
        r_message = ("Invalid preamble: ")

        # Then
        with self.assertRaisesRegexp(ValueError, r_message):
            parse(package_string)

        # Given
        package_string = "numpy 1.8.0-1 depends (nose >= 1.3.2)"
        r_message = ("Invalid preamble: ")

        # Then
        with self.assertRaisesRegexp(ValueError, r_message):
            parse(package_string)

        # Given
        package_string = "numpy; depends (nose >= 1.3.2)"
        r_message = ("Invalid preamble: ")

        # Then
        with self.assertRaisesRegexp(ValueError, r_message):
            parse(package_string)

        # Given
        package_string = "numpy 1.8.0-1; conflicts (nose >= 1.3.2)"
        r_message = ("Invalid package string. "
                     "Unknown constraint kind: 'conflicts'")

        # When
        with self.assertRaisesRegexp(ValueError, r_message):
            parse(package_string)

    def test_simple(self):
        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = "numpy 1.8.0-1; depends (nose == 1.3.4-1)"

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']
        install_requires = dict(package['install_requires'])

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertTrue("nose" in install_requires)
        self.assertEqual(install_requires["nose"], (('== 1.3.4-1',),))

    def test_unversioned(self):
        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = "numpy 1.8.0-1; depends (nose, matplotlib == 1.3.2-1)"

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']
        install_requires = dict(package['install_requires'])

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertTrue("nose" in install_requires)
        self.assertEqual(install_requires["nose"], (('',),))
        self.assertEqual(install_requires["matplotlib"], (('== 1.3.2-1',),))

        # Given
        package_string = "numpy 1.8.0-1; depends (nose *, zope == 1.3.2-1)"

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']
        install_requires = dict(package['install_requires'])

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertTrue("nose" in install_requires)
        self.assertEqual(install_requires["nose"], (('*',),))
        self.assertEqual(install_requires["zope"], (('== 1.3.2-1',),))

    def test_special_characters(self):
        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = "shiboken_debug 1.2.2-5"

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']

        # Then
        self.assertEqual(name, "shiboken_debug")
        self.assertEqual(version, V("1.2.2-5"))

        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = '; '.join((
            "scikits.image 0.10.0-1",
            "depends (scipy ^= 0.14.0, pil, zope.distribution *)"
        ))
        r_install_requires = (
            ('pil', (('',),)),
            ('scipy', (('^= 0.14.0',),)),
            ('zope.distribution', (('*',),))
        )

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']
        install_requires = package['install_requires']

        # Then
        self.assertEqual(name, "scikits.image")
        self.assertEqual(version, V("0.10.0-1"))
        self.assertEqual(install_requires, r_install_requires)

    def test_multiple(self):
        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = "numpy 1.8.0-1; depends (nose => 1.3, nose < 1.4)"

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']
        install_requires = dict(package['install_requires'])

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertTrue("nose" in install_requires)
        self.assertEqual(install_requires["nose"], (('=> 1.3', '< 1.4'),))

    def test_no_dependencies(self):
        # Given
        parse = PrettyPackageStringParser(V).parse
        package_string = "numpy 1.8.0-1"

        # When
        package = parse(package_string)
        name = package['distribution']
        version = package['version']

        # Then
        self.assertEqual(name, "numpy")
        self.assertEqual(version, V("1.8.0-1"))
        self.assertNotIn('install_requires', package)


class TestPackagePrettyString(unittest.TestCase):
    def test_simple(self):
        # Given
        install_requires = (("MKL", (("== 10.3-1",),)),)
        package = PackageMetadata(u"numpy", V("1.8.1-1"), install_requires)

        r_pretty_string = u"numpy 1.8.1-1; depends (MKL == 10.3-1)"

        # When
        pretty_string = package_to_pretty_string(package)

        # Then
        self.assertEqual(pretty_string, r_pretty_string)

        # Given
        install_requires = (("nose", (("",),)),)
        package = PackageMetadata(u"numpy", V("1.8.1-1"), install_requires)

        r_pretty_string = "numpy 1.8.1-1; depends (nose)"

        # When
        pretty_string = package_to_pretty_string(package)

        # Then
        self.assertEqual(pretty_string, r_pretty_string)


class TestToPackage(unittest.TestCase):

    def test_simple(self):
        # Given
        s = u"zope.deprecated_ 2"
        parser = PrettyPackageStringParser(V)

        # When
        package = parser.parse_to_package(s)

        # Then
        self.assertEqual(package.name, "zope.deprecated_")
        self.assertEqual(package.version, V('2'))
        self.assertEqual(package.install_requires, ())

    def test_with_depends(self):
        # Given
        s = u"numpy 1.8.1; depends (MKL ^= 10.3)"
        parser = PrettyPackageStringParser(V)

        # When
        package = parser.parse_to_package(s)

        # Then
        self.assertEqual(package.name, "numpy")
        self.assertEqual(package.version, V('1.8.1'))
        self.assertEqual(package.install_requires, (("MKL", (("^= 10.3",),)),))
