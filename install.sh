#! /bin/sh

REPOBEE_INSTALL_DIR="$HOME/.repobee"
REPOBEE_BIN_DIR="$REPOBEE_INSTALL_DIR/bin"
REPOBEE_REPO_DIR="$REPOBEE_INSTALL_DIR/repobee_git"
REPOBEE_HTTPS_URL="https://github.com/repobee/repobee"
REPOBEE_EXECUTABLE="$REPOBEE_BIN_DIR/repobee"
REPOBEE_VERSION="v2.4.0"
REPOBEE_ARCHIVE_URL="$REPOBEE_HTTPS_URL/archive/$REPOBEE_VERSION.tar.gz"

VENV_DIR="$REPOBEE_INSTALL_DIR/env"
REPOBEE_PYTHON="$VENV_DIR/bin/python"

function install() {
    if [ -d "$REPOBEE_INSTALL_DIR" ]; then
        echo "Found RepoBee installation at $REPOBEE_INSTALL_DIR, attempting repair and upgrade ..."
    fi

    check_prerequisites
    install_repobee
}

function check_prerequisites() {
    # check that Python 3.6+, pip and Git are installed
    installed_python=$(find_python)
    if [ -z "$installed_python" ]; then
        echo "Cannot find any compatible version of Python installed."
        echo "Please install Python 3.6 or higher and then rerun this script."
        echo "See https://www.python.org/downloads/ for a Python installer."
        exit 1
    else
        echo "Found $installed_python executable"
    fi

    git --version &> /dev/null
    if [ $? != 0 ]; then
        echo "Git is not installed."
        echo "Please install Git and then rerun this script."
        echo "See https://git-scm.com/downloads for Git install instructions"
        exit 1
    else
        echo "Found $(git --version)"
    fi
}

function install_repobee() {
    echo "Installing RepoBee at $REPOBEE_INSTALL_DIR"

    #$(find_python) -m venv "$VENV_DIR" || exit 1
    ensure_pip_installed

    echo "Installing RepoBee $REPOBEE_VERSION"
    pip_install_quiet_failfast "$REPOBEE_ARCHIVE_URL"
    create_repobee_executable

    echo "Checking PATH"
    pip_install_quiet_failfast userpath
    "$REPOBEE_PYTHON" -m userpath verify "$REPOBEE_BIN_DIR" &> /dev/null \
    && echo "PATH OK" \
    || {
        echo "Adding $REPOBEE_BIN_DIR to PATH to make the repobee program accessible"
        "$REPOBEE_PYTHON" -m userpath prepend "$REPOBEE_BIN_DIR" || exit 1
        echo "$REPOBEE_BIN_DIR added to PATH"
    }
}

function find_python() {
    for python_version in "3.6" "3.7" "3.8"; do
        python_cmd="python$python_version"
        $python_cmd --version &> /dev/null
        if [ $? = 0 ]; then
            echo $python_cmd
            break
        fi
    done
}

function pip_install_quiet_failfast() {
    "$REPOBEE_PYTHON" -m pip install --upgrade $1 > /dev/null || {
        echo "There was a problem installing $1"
        exit 1
    }
}

function ensure_pip_installed() {
    "$REPOBEE_PYTHON" -m pip install --upgrade pip &> /dev/null || {
        echo "Installing pip"
        get_pip="$REPOBEE_INSTALL_DIR/get-pip.py"
        curl https://bootstrap.pypa.io/get-pip.py -o "$get_pip" || exit 1
        "$REPOBEE_PYTHON" "$get_pip" || exit 1
    }
}

function create_repobee_executable() {
    echo "Creating RepoBee executable"

    mkdir -p "$REPOBEE_BIN_DIR"
    echo "#! /bin/sh
\"$REPOBEE_PYTHON\" -m repobee" '$@' > "$REPOBEE_EXECUTABLE"
    chmod +x "$REPOBEE_EXECUTABLE"

    echo "RepoBee exuctable created at $REPOBEE_EXECUTABLE"
}

install

echo ""
echo "RepoBee was installed successfully. To uninstall, simply remove the directory at $REPOBEE_INSTALL_DIR"
echo "Please start a new shell/terminal session to ensure that the PATH is updated."
echo "If you are having trouble, please visit the FAQ at https://repobee.readthedocs.io/troubleshoot.html"
