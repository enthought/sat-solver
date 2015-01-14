"""
A SAT solver which follows the Minisat approach.

"""
from collections import defaultdict, deque, OrderedDict

from .utils import value


class Constraint(object):
    pass


class Clause(Constraint):

    def __init__(self, lits, learned=False):
        self.learned = learned
        self.lits = OrderedDict.fromkeys(lits).keys()

    def rewatch(self, assignments, lit):
        """Find a new literal to watch.

        The running assumption is that watched literals should either be True
        or not assigned (None). If a watched literal becomes False, a new watch
        must be found. When this is not possible, the other watched literal
        is necessarily True (unit information).

        Returns
        -------
        unit_information: Literal or None
            A literal which has become true under the current assignments.

        Note that this method does not check whether unit propagation leads to
        a conflict.

        """
        # Internal assumption: the watched literals are the first elements of
        # lits. If necessary, this method will re-order some of the literals to
        # keep this assumption.
        lits = self.lits
        assert -lit in lits[:2]

        if lits[0] == -lit:
            lits[0], lits[1] = lits[1], -lit

        if value(lits[0], assignments) is True:
            # This clause has been satisfied, add it back to the watch list. No
            # unit information can be deduced.
            return None

        # Look for another literal to watch, and switch it with lit[1] to keep
        # the assumption on the watched literals in place.
        for n, other in enumerate(lits[2:]):
            if value(other, assignments) is not False:
                # Found a new literal that could serve as a watch.
                lits[1], lits[n + 2] = other, -lit
                return None

        # Clause is unit under assignment. Return the literal that can be
        # propagated.
        return lits[0]

    def calculate_reason(self, p=None):
        """For a conflicting clause, return the reason for propagating p.

        For example, if the clause is x \/ y \/ z, then the reason for
        propagating x is -y /\ -z. By convention, f the literal p does not
        occur in the clause, the negative of the whole clause is returned.

        """
        # TODO: We can speed this up if we can guarantee that we'll only ask
        # for the reason of the first literal, as is the case in the Minisat
        # paper.
        return [-lit for lit in self.lits if lit != p]

    def __len__(self):
        return len(self.lits)

    def __getitem__(self, s):
        return self.lits[s]

    def __repr__(self):
        return "Clause({}, learned={})".format(self.lits, self.learned)


class Solver(object):

    def __init__(self):

        self.clauses = []
        self.watches = defaultdict(list)

        self.assignments = {}

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
        self.reason = {}

        # Whether the system is satisfiable.
        self.status = None

    def add_clause(self, clause):
        """ Add a new clause to the solver.
        """
        # TODO: Do some simplifications, and check whether clause contains p
        # and -p at the same time.

        if isinstance(clause, list):
            clause = Clause(clause, learned=False)

        if len(clause) == 0:
            # Clause is guaranteed to be false under the current variable
            # assignments.
            self.status = False
        elif len(clause) == 1:
            # Unit facts are enqueued.
            self.enqueue(clause[0])
        else:
            p, q = clause[:2]
            self.watches[-p].append(clause)
            self.watches[-q].append(clause)

            self.clauses.append(clause)

    def _setup_assignments(self):
        """Initialize assignments table.
        """
        self.assignments = {
            abs(lit): None for clause in self.clauses for lit in clause
        }

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
                    if value(unit, self.assignments) is False:
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
        status = value(lit, self.assignments)
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
            self.reason[abs(lit)] = cause

            return True

    def search(self):
        """ Return next solution, or False if unsatisfiable.
        """
        root_level = self.decision_level
        while True:
            conflict = self.propagate()
            if conflict is None:
                if self.number_assigned == self.number_variables:
                    # Model found.
                    return self.assignments.copy()  # Do something better...
                else:
                    # New variable decision.

                    # TODO As we don't record variable activities, we simply
                    # select the next unassigned variable.
                    p = next(key for key, value in self.assignments.items()
                             if value is None)
                    self.assume(p)
            else:
                # Conflict!
                if root_level == self.decision_level:
                    return False

                learned_clause, bt_level = self.analyze(conflict)
                self.cancel_until(max(bt_level, root_level))
                self.record(learned_clause)

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
                conflict = self.reason[abs(p)]
                self.undo_one()
                if abs(p) in seen:
                    break

            counter -= 1
            if counter == 0:
                break

        learned_lits.append(-p)  # At this point p is the UIP.
        return Clause(learned_lits, learned=True), btlevel

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
        max_i = max(enumerate([self.levels.get(abs(lit), 0) for lit in lits]),
                    key=lambda (n, level): level)[0]
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
        self.reason[v] = None
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
        for _ in xrange(c):
            self.undo_one()

    def assume(self, lit):
        self.trail_lim.append(len(self.trail))  # FIXME: This is fishy.
        return self.enqueue(lit)

    @property
    def number_assigned(self):
        """ Return the number of currently assigned variables.
        """
        return len([value for value in self.assignments.values()
                    if value is not None])

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
