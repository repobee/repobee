#! /bin/sh

REPOBEE_INSTALL_DIR="$HOME/.repobee"
REPOBEE_REPO_DIR="$REPOBEE_INSTALL_DIR/repobee_git"
REPOBEE_HTTPS_URL="https://github.com/repobee/repobee"
REPOBEE_EXECUTABLE="$REPOBEE_INSTALL_DIR/repobee"
REPOBEE_VERSION="v2.4.0"
REPOBEE_ARCHIVE_URL="$REPOBEE_HTTPS_URL/archive/$REPOBEE_VERSION.tar.gz"

VENV_DIR="$REPOBEE_INSTALL_DIR/env"
REPOBEE_PYTHON="$VENV_DIR/bin/python"

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

function install_repobee() {
    echo "Installing RepoBee at $REPOBEE_INSTALL_DIR"

    "$installed_python" -m venv "$VENV_DIR" || exit 1
    "$REPOBEE_PYTHON" -m pip install --upgrade pip || exit 1

    echo ""
    echo "Installing RepoBee $REPOBEE_VERSION"
    echo ""
    "$REPOBEE_PYTHON" -m pip install --upgrade "$REPOBEE_ARCHIVE_URL" || { echo "RepoBee $REPOBEE_VERSION does not appear to exist"; exit 1; }

    echo "Creating RepoBee executable"
    echo "#! /bin/sh
\"$REPOBEE_PYTHON\" -m repobee" '$@' > "$REPOBEE_EXECUTABLE"
    chmod +x "$REPOBEE_EXECUTABLE"

    echo "Checking PATH"
    "$REPOBEE_PYTHON" -m pip install userpath &> /dev/null || exit 1
    "$REPOBEE_PYTHON" -m userpath verify "$REPOBEE_EXECUTABLE" || {
        "$REPOBEE_PYTHON" -m userpath prepend "$REPOBEE_EXECUTABLE" &> /dev/null || { echo "Failed to add $REPOBEE_EXECUTABLE to PATH, please do so manually"; exit 1; }
        echo "$REPOBEE_EXECUTABLE added to PATH. Start a new shell and the repobee program will be available."
    }
}

function install() {
    # check that Python 3.6+, pip and Git are installed
    installed_python=$(find_python)
    if [ -z "$installed_python" ]; then
        echo "Please install python 3.6 or higher: https://www.python.org/downloads/"
        exit 1
    else
        echo "Using $installed_python"
    fi

    $installed_python -m pip --version &> /dev/null
    if [ $? != 0 ]; then
        echo "pip not installed for $installed_python. Please install pip: https://pip.pypa.io/en/stable/installing/"
        exit 1
    fi

    git --version &> /dev/null
    if [ $? != 0 ]; then
        echo "Please install Git: https://git-scm.com/downloads"
        exit 1
    else
        echo "Using $(git --version)"
    fi

    if [ -d "$REPOBEE_INSTALL_DIR" ]; then
        echo "Found RepoBee installation at $REPOBEE_INSTALL_DIR, upgrading ..."
    fi

    install_repobee
}

install

