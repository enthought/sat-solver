import ast
import os
import re
import subprocess


_R_RC = re.compile("rc(\d+)$")


def parse_version(path):
    with open(path) as fp:
        return _AssignmentParser().parse(fp.read())["version"]


def write_version_py(filename, major, minor, micro, is_released,
                     previous_version=None):
    template = """\
# THIS FILE IS GENERATED FROM SETUP_EXT
version = '{final_version}'
full_version = '{full_version}'
git_revision = '{git_revision}'
is_released = {is_released}

msi_version = '{msi_version}'

version_info = {version_info}
"""
    version = full_version = "{0}.{1}.{2}".format(major, minor, micro)
    is_released = is_released

    if not os.path.exists('.git'):
        if os.path.exists(filename):
            return
        else:
            raise RuntimeError(
                "No git repo found and no {!r} found !".format(filename)
            )

    git_rev = _git_version()
    if previous_version is not None:
        build_number = _compute_build_number("v" + previous_version)
    else:
        try:
            out = _minimal_ext_cmd(['git', 'rev-list', '--count', 'HEAD'])
            build_number = int(out.strip().decode('ascii'))
        except OSError:
            build_number = 0

    if _is_rc(version):
        release_level = "rc"
    elif not is_released:
        release_level = "dev"
    else:
        release_level = "final"

    if not is_released:
        full_version += '.dev' + str(build_number)
        if _is_rc(version):
            serial = _rc_number(version)
        else:
            serial = build_number
        final_version = full_version
    else:
        final_version = version
        if _is_rc(version):
            serial = _rc_number(version)
        else:
            serial = 0

    version_info = (major, minor, micro, release_level, serial)
    msi_version = ".".join(str(i) for i in version_info[:3] + (build_number,))

    with open(filename, "wt") as fp:
        data = template.format(
            final_version=final_version, full_version=full_version,
            git_revision=git_rev, is_released=is_released,
            version_info=version_info, msi_version=msi_version,
        )
        fp.write(data)


def _git_version():
    """ Return git revision or "Unknown" if cannot be computed
    """
    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        git_revision = out.strip().decode('ascii')
    except OSError:
        git_revision = "Unknown"

    return git_revision


def _is_rc(version):
    return _R_RC.search(version) is not None


def _rc_number(version):
    m = _R_RC.search(version)
    assert m is not None
    return m.groups()[0]


def _compute_build_number(from_tag):
    cmd = ["git", "rev-list", from_tag + "..", "--count"]
    output = _minimal_ext_cmd(cmd)
    build_number = int(output.strip())
    assert build_number < 2 ** 16, "build number overflow"
    return build_number


def _minimal_ext_cmd(cmd):
    # construct minimal environment
    env = {}
    for k in ['SYSTEMROOT', 'PATH']:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    # LANGUAGE is used on win32
    env['LANGUAGE'] = 'C'
    env['LANG'] = 'C'
    env['LC_ALL'] = 'C'
    return subprocess.check_output(cmd, env=env)


class _AssignmentParser(ast.NodeVisitor):
    def __init__(self):
        self._data = {}

    def parse(self, s):
        self._data.clear()

        root = ast.parse(s)
        self.visit(root)
        return self._data

    def generic_visit(self, node):
        if type(node) != ast.Module:
            raise ValueError(
                "Unexpected expression @ line {0}".format(node.lineno),
                node.lineno
            )
        super(_AssignmentParser, self).generic_visit(node)

    def visit_Assign(self, node):
        value = ast.literal_eval(node.value)
        for target in node.targets:
            self._data[target.id] = value
