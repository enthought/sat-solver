from setuptools import setup


PACKAGES = [
    "simplesat",
    "simplesat.constraints",
    "simplesat.constraints.tests",
    "simplesat.examples",
    "simplesat.sat",
    "simplesat.sat.policy",
    "simplesat.sat.tests",
    "simplesat.tests",
    "simplesat.test_data",
    "simplesat.utils",
    "simplesat.utils.tests",
]

PACKAGE_DATA = {
    "simplesat.tests": ["*.yaml"],
    "simplesat.test_data": ["indices/*.json"],
}


setup(
    name='simplesat',
    version='0.2.0.dev1',
    author='Enthought, Inc',
    author_email='info@enthought.com',
    url='https://github.com/enthought/sat-solvers',
    description='Simple SAT solvers for use in Enstaller',
    packages=PACKAGES,
    package_data=PACKAGE_DATA,
    install_requires=["attrs >= 15.2.0", "okonomiyaki == 0.14.0", "six >= 1.9.0"],
)
