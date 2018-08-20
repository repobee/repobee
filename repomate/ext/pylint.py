from gits_pet.hookspec import hookimpl
import subprocess
import os
import daiquiri
from gits_pet import tuples

LOGGER = daiquiri.getLogger(name=__file__)


def _python_files(root):
    for cwd, dirs, files in os.walk(root):
        for file in files:
            if file.endswith('.py'):
                yield cwd, file


@hookimpl
def act_on_cloned_repo(path):
    """Run pylint on all Python files in a repo."""
    python_files = list(_python_files(path))

    if not python_files:
        msg = "no .py files found"
        status = "warning"
        return tuples.HookResult('pylint', status, msg)

    linted_files = []
    for cwd, py_file in python_files:
        LOGGER.info("running pylint on {}".format(py_file))
        infile = os.path.join(cwd, py_file)
        outfile = os.path.join(cwd, "{}.lint".format(py_file))
        command = 'pylint {}'.format(infile).split()
        proc = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with open(outfile, 'w', encoding='utf8') as f:
            f.write(proc.stdout.decode('utf8'))
        linted_files.append(py_file)

    msg = "linted files: {}".format(", ".join(linted_files))
    return tuples.HookResult(hook="pylint", status="success", msg=msg)
