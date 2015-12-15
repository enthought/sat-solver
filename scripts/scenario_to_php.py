import argparse
import os.path
import sys

import jinja2

from simplesat.test_utils import Scenario
from simplesat.utils._composer_utils import scenario_to_php_template_variables


def main(argv=None):
    argv = argv or sys.argv[1:]

    default_composer_root = os.path.expanduser(
        os.path.join("~/src/projects/composer-git")
    )

    p = argparse.ArgumentParser()
    p.add_argument("scenario", help="Path to the YAML scenario file.")
    p.add_argument("templates", help="PHP templates.", nargs="+")
    p.add_argument("--composer-root", help="Composer root.",
                   default=default_composer_root)

    ns = p.parse_args(argv)

    remote_definition = "remote.json"
    installed_definition = "installed.json"

    scenario = Scenario.from_yaml(ns.scenario)

    template_variables = scenario_to_php_template_variables(scenario,
                                                            remote_definition,
                                                            installed_definition)
    template_variables["composer_bootstrap"] = os.path.join(
        ns.composer_root, "src", "bootstrap.php"
    )

    for template in ns.templates:
        suffix = ".in"
        assert template.endswith(suffix), \
               "Templates should end w/ the {0!r} suffix".format(suffix)

        with open(template, "rt") as fpin:
            output = template[:-len(suffix)]
            with open(output, "wt") as fpout:
                data = jinja2.Template(fpin.read()).render(**template_variables)
                fpout.write(data)


if __name__ == "__main__":
    main()
