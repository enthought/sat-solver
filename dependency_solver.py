import operator

from enstaller.new_solver.pool import Pool
from enstaller.new_solver.requirement import Requirement
from enstaller.new_solver.tests.common import repository_from_index
from enstaller.solver import Request
from enstaller.versions.enpkg import EnpkgVersion

from simplesat.rules_generator import RulesGenerator

V = EnpkgVersion.from_string


repository = repository_from_index("index.json")
pool = Pool([repository])

requirement_str = "numpy < 2.0"
requirement = Requirement._from_string(requirement_str)

if False:
    candidates = pool.what_provides(requirement)
    for candidate in sorted(candidates,
                            key=operator.attrgetter("version")):
        print pool.id_to_string(candidate.id)

request = Request()
request.install(requirement)

rules_generator = RulesGenerator(pool, request)
for rule in rules_generator.iter_rules():
    print rule.to_string(pool)
