class DefaultPolicy(object):
    def get_next_package_id(self, assignments, _):
        # Given a dictionary of partial assignments, get an undecided variable
        # to be decided next.
        undecided = [
            package_id for package_id, status in assignments.iteritems()
            if status is None
        ]
        return undecided[0]
