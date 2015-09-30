def value(lit, assignments):
    """ Value of a literal given variable assignments.
    """
    status = assignments.get(abs(lit))
    if status is None:
        return None
    is_conjugated = lit < 0
    return is_conjugated is not status
