#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

import csv
import string

_fro = (string.ascii_lowercase +
        string.ascii_uppercase +
        string.digits)
_to = ('a' * len(string.ascii_lowercase) +
       'A' * len(string.ascii_uppercase) +
       '0' * len(string.digits))
TRANS = string.maketrans(_fro, _to)


def proc(s):
    return len(set(string.translate(s, TRANS)))


def make_names_vers(lines):
    reader = csv.reader(lines)
    # Ignore header
    next(reader)

    for row in reader:
        name = row[1].strip()
        ver = row[2].strip()
        yield (name, ver)


def build_terrible_packages(names, vers):
    worst_names = sorted(names, key=proc, reverse=True)
    worst_versions = sorted(vers, key=proc, reverse=True)
    return tuple(' '.join(s) for s in zip(worst_names, worst_versions))


def build_long_packages(names, vers):
    worst_names = sorted(names, key=len, reverse=True)
    worst_versions = sorted(vers, key=len, reverse=True)
    return tuple(' '.join(s) for s in zip(worst_names, worst_versions))


def main():
    """Run main."""
    import argparse
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('index_file', type=argparse.FileType())
    parser.add_argument('out_file')
    args = parser.parse_args(['brood-test-jaguar-dump.csv', 'out.txt'])
    names, vers = zip(*make_names_vers(args.index_file))
    terribles = build_terrible_packages(names, vers)
    longs = build_long_packages(names, vers)

    worsts = sorted(
        set(terribles[:100] + terribles[-10:] + longs[:100] + longs[-10:]),
        key=len)

    with open(args.out_file, 'w') as f:
        f.writelines('\n'.join(worsts))
    return 0


if __name__ == '__main__':
    main()
