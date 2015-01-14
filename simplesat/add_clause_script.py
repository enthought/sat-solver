from simplesat.api import Solver, Clause

x = Clause(range(100))
s = Solver()
s.add_clause(x)
