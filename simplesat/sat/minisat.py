"""
A SAT solver which follows the Minisat approach.

"""
from __future__ import absolute_import

from collections import defaultdict, deque, OrderedDict

from six.moves import range

from simplesat.errors import SatisfiabilityError
from .assignment_set import AssignmentSet
from .clause import Clause
from .policy import DefaultPolicy
from simplesat.utils import timed_context


class UNSAT(object):

    """An unsatisfiable set of boolean clauses."""

    def __init__(self, conflict, learned):
        self._conflict = conflict
        self._clauses = [conflict, learned] + learned.trail + conflict.trail
        self._find_requirement_time = None
        with timed_context("Find Requirements") as self._find_requirement_time:
            seen = set()
            self._requirements = set(e.rule._requirement
                                     for c in self._clauses
                                     for e in self.expand(c, seen))
            self._requirements.discard(None)

    def expand(self, clause, seen):
        try:
            if clause.learned:
                if clause not in seen:
                    seen.add(clause)
                    trail = (e for c in clause.trail
                             for e in self.expand(c, seen))
                else:
                    trail = ()
            else:
                trail = (clause,)
        except AttributeError:
            trail = ()
        return trail

    def to_string(self, pool=None, detailed=False):
        pretty_reqs = [str(r) for r in self._requirements]
        if len(self._requirements) == 2:
            msg = "Requirement {!r} conflicts with {!r}"
            reason = msg.format(*pretty_reqs)
        else:
            reason = "Conflicting requirements:\n\t"
            reason += '\n\t'.join(pretty_reqs)
        return reason

class MiniSATSolver(object):
    @classmethod
    def from_rules(cls, rules, policy=None):
        """
        Construct a SAT solver from a rules generator.

        Parameters
        ----------
        rules: RulesGenerator
        policy: IPolicy
            The policy to use for this SAT solver.

        Returns
        -------
        solver: MiniSATSolver.

        """
        solver = cls(policy)
        for rule in rules:
            solver.add_clause(rule.literals, rule=rule)
        solver._setup_assignments()
        return solver

    def __init__(self, policy=None):

        self.clauses = []
        self.watches = defaultdict(list)

        self.assignments = AssignmentSet()

        # The most recent (non-None) assigned value of each literal
        self.most_recent_assignments = {}

        # A list of literals which become successively true (because of direct
        # assignment, or by unit propagation).
        self.levels = defaultdict(int)

        self.prop_queue = deque()

        # A list of all the decisions that we've made so far.
        self.trail = []

        # Keeps track of the independent assumptions so far. Each entry in
        # trail_lim is an index pointing to an assumption in trail. TODO:
        # Structure self.trail so that it keeps track of decisions per level.
        self.trail_lim = []

        # For each variable assignment, a reference to the clause that forced
        # this assignment.
        self.assigning_clause = OrderedDict()

        # Whether the system is satisfiable.
        self.status = None

        self._policy = policy or DefaultPolicy()

    def add_clause(self, clause, rule=None):
        """ Add a new clause to the solver.
        """
        # TODO: Do some simplifications, and check whether clause contains p
        # and -p at the same time.

        if not isinstance(clause, Clause):
            clause = Clause(clause, learned=False, rule=rule)

        if len(clause) == 0:
            # Clause is guaranteed to be false under the current variable
            # assignments.
            self.status = False
        elif len(clause) == 1:
            # Unit facts are enqueued.
            self.enqueue(clause[0], cause=clause)
        else:
            p, q = clause[:2]
            self.watches[-p].append(clause)
            self.watches[-q].append(clause)

            self.clauses.append(clause)

    def _setup_assignments(self):
        """Initialize assignments table.
        """
        variables = {abs(lit) for clause in self.clauses for lit in clause}
        assignments = self.assignments
        for variable in variables:
            if variable not in assignments:
                assignments[variable] = None

    def propagate(self):
        while len(self.prop_queue) > 0:
            lit = self.prop_queue.popleft()
            clauses = self.watches[lit]
            self.watches[lit] = []

            while len(clauses) > 0:
                clause = clauses.pop()
                unit = clause.rewatch(self.assignments, lit)

                # Re-insert in the appropriate watch list.
                self.watches[-clause.lits[1]].append(clause)

                # Deal with unit clauses.
                if unit is not None:
                    # TODO Refactor this to take into account the return value
                    # of enqueue().
                    if self.assignments.value(unit) is False:
                        # Conflict. Clear the queue and re-insert the remaining
                        # unwatched clauses into the watch list.
                        self.prop_queue.clear()
                        for remaining in clauses:
                            self.watches[lit].append(remaining)
                        return clause
                    else:
                        # Non-conflicting unit literal.
                        self.enqueue(unit, clause)

    def enqueue(self, lit, cause=None):
        """ Enqueue a new true literal.
        """
        status = self.assignments.value(lit)
        if status is not None:
            # Known fact. Don't enqueue, but return whether this fact
            # contradicts the earlier assignment.
            return status
        else:
            # New fact, store it.
            self.assignments[abs(lit)] = (lit > 0)

            self.prop_queue.append(lit)
            self.trail.append(lit)
            self.levels[abs(lit)] = self.decision_level
            self.assigning_clause[abs(lit)] = cause
            self.most_recent_assignments[abs(lit)] = ((lit > 0), cause)

            return True

    def search(self):
        """ Return next solution or Raise SatisfiabilityError if unsatisfiable.
        """
        root_level = self.decision_level
        while True:
            conflict_clause = self.propagate()
            if conflict_clause is None:
                if self.number_assigned == self.number_variables:
                    # Model found.
                    return self.assignments.copy()  # Do something better...
                else:
                    # New variable decision.
                    p = self._policy.get_next_package_id(
                        self.assignments,
                        self.clauses,
                    )

                    self.assume(p)
            else:
                # Conflict!
                learned_clause, bt_level = self.analyze(conflict_clause)
                if root_level == self.decision_level:
                    conflict = UNSAT(conflict_clause, learned_clause)
                    raise SatisfiabilityError(conflict)

                self.cancel_until(max(bt_level, root_level))
                self.record(learned_clause)

    def validate(self, solution_map):
        """Check whether a given set of assignments solves this SAT problem.
        """
        solution_literals = {variable if status else -variable
                             for variable, status in solution_map.items()}
        # True if any clause has no assigned literals and thus is undetermined
        has_unknown_clause = any(solution_literals.isdisjoint(clause.lits)
                                 for clause in self.clauses)
        return not has_unknown_clause

    def analyze(self, conflict):
        """ Produce a reason clause for a conflict.
        """
        p = None  # Will hold the UIP at the end of the search.

        # A tally of the number of literals encountered so far in the current
        # decision level, and downstream from the UIP.
        counter = 0
        # Variables that we've encountered during the search.
        seen = set()

        # Literals for the clause that we're learning.
        learned_lits = []
        # Level to backtrack to.
        btlevel = 0

        clause_trail = [conflict]

        while True:
            reason = conflict.calculate_reason(p)

            # Trace reason for current p.
            for lit in reason:
                var = abs(lit)
                if var not in seen:
                    seen.add(var)
                    if self.levels[var] == self.decision_level:
                        # A new literal on the current decision level.
                        counter += 1
                    else:
                        # At this point, we don't treat level 0 as
                        # special. Maybe that's a mistake...
                        learned_lits.append(-lit)
                        btlevel = max(btlevel, self.levels[var])

            # Select next literal to look at.
            while True:
                p = self.trail[-1]
                conflict = self.assigning_clause[abs(p)]
                clause_trail.append(conflict)
                self.undo_one()
                if abs(p) in seen:
                    break

            counter -= 1
            if counter == 0:
                break

        learned_lits.append(-p)  # At this point p is the UIP.
        return Clause(learned_lits, learned=True, trail=clause_trail), btlevel

    def record(self, learned_clause):  # Needs test.
        """Drive the backtracking by adding a learned clause, which is unit by
        assumption.

        """
        # Reorder the learned clause, so that lits[0] is the asserting literal,
        # and lits[1] is the literal with highest decision level. This literal
        # will first become unbound by backtracking.
        lits = learned_clause.lits
        lits[0], lits[-1] = lits[-1], lits[0]

        # Index of the literal with the highest decision level.
        def key(arg):
            n, level = arg
            return level
        max_i = max(enumerate([self.levels.get(abs(lit), 0) for lit in lits]),
                    key=key)[0]
        if len(lits) >= 2:
            lits[1], lits[max_i] = lits[max_i], lits[1]

        self.add_clause(learned_clause)
        self.enqueue(learned_clause.lits[0], learned_clause)

    def undo_one(self):
        """Backtrack by one step.
        """
        p = self.trail.pop()
        v = abs(p)  # Underlying variable
        self.assignments[v] = None
        self.assigning_clause[v] = None
        self.levels[v] = -1  # FIXME Why -1?

    def cancel_until(self, level):
        """Cancel all decisions up a given level.
        """
        while self.decision_level > level:
            self.cancel()

    def cancel(self):
        """Undo all decisions in the current decision level.
        """
        # Taken verbatim from Minisat paper.
        c = len(self.trail) - self.trail_lim.pop()
        for _ in range(c):
            self.undo_one()

    def assume(self, lit, cause="assumption"):
        self.trail_lim.append(len(self.trail))  # FIXME: This is fishy.
        return self.enqueue(lit, cause="assumption")

    @property
    def number_assigned(self):
        """ Return the number of currently assigned variables.
        """
        return self.assignments.num_assigned

    @property
    def number_variables(self):
        """ Return the number of variables in the SAT problem.
        """
        return len(self.assignments)

    @property
    def decision_level(self):
        """ Return the number of independent assumptions made so far.
        """
        return len(self.trail_lim)
