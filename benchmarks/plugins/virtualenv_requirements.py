# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import, division, unicode_literals, print_function
)

import os

from asv.plugins.virtualenv import Virtualenv
from asv.console import log
from asv import util


class VirtualenvFromRequirmentsFile(Virtualenv):
    """
    Manage an environment using virtualenv with dependencies from a
    requirements file.
    """
    tool_name = "virtualenv-requirements"

    def __init__(self, conf, python, executable):
        """
        Parameters
        ----------
        conf : Config instance

        python : str
            Version of Python.  Must be of the form "MAJOR.MINOR".

        executable : str
            Path to Python executable.

        requirements : dict
            Dictionary mapping a PyPI package name to a version
            identifier string.
        """
        super(VirtualenvFromRequirmentsFile, self).__init__(
            conf, python, executable)
        try:
            self._requirements_file = conf.requirements_file
        except AttributeError:
            raise util.UserError(
                "No requirements_file specified in config file.")

    def build_project(self, commit_hash):
        self.checkout_project(commit_hash)
        self._install_requirements_file()
        log.info("Building for {0}".format(self.name))
        self.run(['setup.py', 'build'], cwd=self._build_root)
        return self._build_root

    def _install_requirements_file(self):
        log.info("Installing requirements file for {0}".format(self.name))
        req_file = os.path.join(self._build_root, self._requirements_file)
        self.run_executable('pip', ['install', '-r', req_file])
