import enum
import io
import pkgutil

from enstaller.new_solver import Pool

from simplesat.errors import SatisfiabilityError
from simplesat.sat import MiniSATSolver
from simplesat.sat.policy import InstalledFirstPolicy
from simplesat.test_utils import Scenario
from simplesat.transaction import Transaction

try:
    from simplesat.dependency_solver import (
        create_rules_and_initialize_policy, compute_solution_ids)
except ImportError:
    import collections
    from operator import attrgetter
    from egginst.errors import NoPackageFound
    from enstaller.solver import JobType
    from simplesat.dependency_solver import _connected_packages
    from simplesat.rules_generator import RulesGenerator

    def create_rules_and_initialize_policy(
            pool, installed_repository, request, policy):

        all_requirement_ids = []

        for job in request.jobs:
            assert job.kind in (
                JobType.install, JobType.remove, JobType.update
            ), 'Unknown job kind: {}'.format(job.kind)

            requirement = job.requirement

            providers = tuple(pool.what_provides(requirement))
            if len(providers) == 0:
                raise NoPackageFound(str(requirement), requirement)

            if job.kind == JobType.update:
                # An update request *must* install the latest package version
                providers = [max(providers, key=attrgetter('version'))]

            requirement_ids = [pool.package_id(p) for p in providers]
            policy.add_requirements(requirement_ids)
            all_requirement_ids.extend(requirement_ids)

        installed_map = collections.OrderedDict()
        for package in installed_repository:
            installed_map[pool.package_id(package)] = package

        rules_generator = RulesGenerator(pool, request, installed_map)
        rules = list(rules_generator.iter_rules())

        return (installed_map, all_requirement_ids, rules)

    def compute_solution_ids(
            pool, installed_dict, requirement_ids, solution, use_pruning=True):
        installed_map = set(installed_dict)
        solution_ids = sorted(solution._assigned_literals,
                              key=lambda lit: abs(lit))
        if use_pruning:
            root_ids = installed_map.union(requirement_ids)
            solution_ids = _connected_packages(solution_ids, root_ids, pool)
        return solution_ids, installed_map


EPD_IRIS_CONFLICT = 'epd_iris_conflict.yaml'
IRIS = 'iris.yaml'


class STAGE(enum.Enum):
    def __new__(cls):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj
    __order__ = ("yaml scenario pool policy rules solver solution"
                 " solution_ids transaction")
    yaml = ()
    scenario = ()
    pool = ()
    policy = ()
    rules = ()
    solver = ()
    solution = ()
    solution_ids = ()
    transaction = ()


class GraduatedSuite(object):

    scenario_names = (EPD_IRIS_CONFLICT, IRIS)
    params = (scenario_names, list(STAGE)[-1:])
    param_names = ("Scenario", "Stage")

    def _STAGES(self):
        return {
            STAGE.yaml: self.get_yaml,
            STAGE.scenario: self.load_scenario,
            STAGE.pool: self.build_pool,
            STAGE.policy: self.build_policy,
            STAGE.rules: self.create_rules,
            STAGE.solver: self.build_solver,
            STAGE.solution: self.solve,
            STAGE.solution_ids: self.compute_solution_ids,
            STAGE.transaction: self.build_transaction,
        }

    def setup(self, scenario_name, stop_before, prefer_installed=True):
        self.scenario_name = scenario_name
        self.prefer_installed = prefer_installed
        self.stop_before = stop_before
        self.STAGES = self._STAGES()

        for stage in STAGE:
            if stage == self.stop_before:
                break
            self.STAGES[stage]()

    def get_yaml(self):
        try:
            yaml_bytes = pkgutil.get_data(
                'simplesat.tests', self.scenario_name)
        except IOError:
            raise NotImplementedError
        self.yaml = yaml_bytes.decode('UTF-8')

    def load_scenario(self):
        fp = io.StringIO(self.yaml)
        self.scenario = Scenario.from_yaml(fp)

    def build_pool(self):
        pool = Pool(self.scenario.remote_repositories)
        pool.add_repository(self.scenario.installed_repository)
        self.pool = pool

    def build_policy(self):
        self.policy = InstalledFirstPolicy(
            self.pool, self.scenario.installed_repository,
            prefer_installed=self.prefer_installed)

    def create_rules(self):
        packed = create_rules_and_initialize_policy(
            self.pool, self.scenario.installed_repository,
            self.scenario.request, self.policy)
        self.installed_dict, self.requirement_ids, self.rules = packed

    def build_solver(self):
        self.solver = MiniSATSolver.from_rules(self.rules, self.policy)

    def solve(self):
        try:
            sol = self.solver.search()
        except SatisfiabilityError:
            sol = None
        self.solution = sol

    def compute_solution_ids(self):
        if self.solution is None:
            raise NotImplementedError
        self.solution_ids, self.installed_map = compute_solution_ids(
            self.pool, self.installed_dict, self.requirement_ids,
            self.solution)

    def build_transaction(self):
        self.transaction = Transaction(
            self.pool, self.solution_ids, self.installed_map)

    def time_stage(self, _, stage):
        self.STAGES[stage]()
