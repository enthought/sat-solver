"""
A SAT solver which follows the Minisat approach.

"""
from collections import defaultdict, deque, OrderedDict


class Constraint(object):
    pass


def value(lit, assignments):
    """ Value of a literal given variable assignments.
    """
    status = assignments.get(abs(lit))
    if status is None:
        return None
    is_conjugated = lit < 0
    return is_conjugated is not status


class Clause(Constraint):

    def __init__(self, lits, learnt=False):
        self.learnt = learnt
        self.lits = OrderedDict.fromkeys(lits).keys()

    # TODO: Name is not really appropriate anymore.
    # TODO: Don't need to do this dance with lit vs. -lit anymore.
    def propagate(self, assignments, lit):
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

    def __len__(self):
        return len(self.lits)

    def __getitem__(self, s):
        return self.lits[s]

    def __repr__(self):
        return "Clause({}, learnt={})".format(self.lits, self.learnt)


class Solver(object):

    def __init__(self):
        self.clauses = []
        self.watches = defaultdict(list)

        self.assignments = {}  # XXX
        self.prop_queue = deque()

        # Whether the system is satisfiable.
        self.status = None

    def add_clause(self, clause, learned=False):
        """ Add a new clause to the solver.
        """
        # TODO: Do some simplifications, and check whether clause contains p
        # and -p at the same time.

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

    def propagate(self):
        while len(self.prop_queue) > 0:
            lit = self.prop_queue.popleft()
            clauses = self.watches[lit]
            self.watches[lit] = []

            while len(clauses) > 0:
                clause = clauses.pop()
                unit = clause.propagate(self.assignments, lit)

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
                            self.watches[-remaining.lits[1]].append(remaining)
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
            return True
