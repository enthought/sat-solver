# -*- coding: utf-8 -*-

from .policy import DefaultPolicy
from .undetermined_clause_policy import (
    LoggedUndeterminedClausePolicy, UndeterminedClausePolicy
)
from .priority_queue_policy import (
    LoggedPriorityQueuePolicty, PriorityQueuePolicy
)

InstalledFirstPolicy = LoggedUndeterminedClausePolicy
