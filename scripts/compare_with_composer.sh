#!/bin/bash

set -eCu


SCENARIO="$1"
shift
TMPDIR=$(mktemp -d)
trap 'rm -r $TMPDIR' EXIT
US="$TMPDIR/us"
THEM="$TMPDIR/them"

set -x
python scripts/solve.py --simple "$@" "$SCENARIO" | sort -k 2 > "$US"
python scripts/scenario_to_php.py --composer-root composer "$SCENARIO" scripts/print_operations.php.in
time php scripts/print_operations.php | sort -k 2 > "$THEM"
diff -y "$US" "$THEM"
