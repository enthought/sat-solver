from setuptools import setup


PACKAGES = [
    "simplesat",
    "simplesat.examples",
    "simplesat.sat",
    "simplesat.sat.tests",
    "simplesat.scripts",
    "simplesat.tests",
]

PACKAGE_DATA = {
    "simplesat.tests": ["*.yaml"],
}


setup(
    name='simplesat',
    version='0.1',
    author='Enthought, Inc',
    author_email='info@enthought.com',
    url='https://github.com/enthought/sat-solvers',
    description='Simple SAT solvers for use in Enstaller',
    packages=PACKAGES,
    package_data=PACKAGE_DATA,
    install_requires=["six >= 1.9.0"],
)
