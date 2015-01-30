from setuptools import setup


setup(
    name='simplesat',
    version='0.1',
    author='Enthought, Inc',
    author_email='info@enthought.com',
    url='https://github.com/enthought/sat-solvers',
    description='Simple SAT solvers for use in Enstaller',
    packages=['simplesat'],
    entry_points="""
        [console_scripts]
            yaml_to_repository=simplesat.scripts.yaml_to_repository:main
    """,
)
