#! /bin/bash

REPOBEE_INSTALL_DIR="$HOME/.repobee"
REPOBEE_BIN_DIR="$REPOBEE_INSTALL_DIR/bin"
REPOBEE_REPO_DIR="$REPOBEE_INSTALL_DIR/repobee_git"
REPOBEE_HTTPS_URL="https://github.com/slarse/repobee"
REPOBEE_EXECUTABLE="$REPOBEE_BIN_DIR/repobee"
REPOBEE_VERSION="issue/420-repobee-installer"
REPOBEE_PIP_URL="git+$REPOBEE_HTTPS_URL.git@$REPOBEE_VERSION"

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
        printf "\nCannot find any compatible version of Python installed.\n"
        echo "Please install Python 3.6 or higher and then rerun this script."
        echo "See https://www.python.org/downloads/ for a Python installer."
        exit 1
    else
        echo "Found $installed_python executable"
    fi

    git --version &> /dev/null
    if [ $? != 0 ]; then
        printf "\nGit is not installed.\n"
        echo "Please install Git and then rerun this script."
        echo "See https://git-scm.com/downloads for Git install instructions"
        exit 1
    else
        echo "Found $(git --version)"
    fi
}

function install_repobee() {
    echo "Installing RepoBee at $REPOBEE_INSTALL_DIR"

    $(find_python) -m venv "$VENV_DIR" &> /dev/null || {
        printf "\nFailed to create a virtual environment for RepoBee.\n"
        echo "This is typically caused by the venv package not being installed."
        printf "If you run Ubuntu/Debian, try running the following commands:\n\n"
        echo "    sudo apt-add-repository universe"
        echo "    sudo apt update"
        echo "    sudo apt install python3-venv"
        printf "\nThen re-execute this script."
        exit 1
    }
    ensure_pip_installed

    echo "Installing RepoBee $REPOBEE_VERSION"
    REPOBEE_PYTHON_INTERPRETER="$REPOBEE_PYTHON" pip_install_quiet_failfast "$REPOBEE_PIP_URL"
    create_repobee_executable

    echo "Checking PATH"
    pip_install_quiet_failfast userpath
    "$REPOBEE_PYTHON" -m userpath verify "$REPOBEE_BIN_DIR" &> /dev/null \
    && echo "PATH OK" || add_to_path
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
        download https://bootstrap.pypa.io/get-pip.py "$get_pip" || exit 1
        "$REPOBEE_PYTHON" "$get_pip" || exit 1
    }
}

function download() {
    # try downloading a file with both curl and wget
    url="$1"
    dst="$2"

    curl --version &> /dev/null && {
        curl "$url" -o "$dst"
        return 0
    }
    wget --version &> /dev/null && {
        wget "$url" -O "$dst"
        return 0
    }
    return 1
}

function create_repobee_executable() {
    echo "Creating RepoBee executable"

    mkdir -p "$REPOBEE_BIN_DIR"
    echo "#! /bin/sh
\"$REPOBEE_PYTHON\" -m repobee" '$@' > "$REPOBEE_EXECUTABLE"
    chmod +x "$REPOBEE_EXECUTABLE"

    echo "RepoBee exuctable created at $REPOBEE_EXECUTABLE"
}

function add_to_path() {
    printf "\n$REPOBEE_BIN_DIR is not on the PATH, so to run RepoBee you must type the full path to $REPOBEE_EXECUTABLE.\n"
    echo "We can add $REPOBEE_BIN_DIR to your PATH by adding it to your profile file (e.g. .bashrc, .zshrc, config.fish, etc), and then you just need to type 'repobee' to run it."
    echo "If you prefer to do this manually, and know how to do it, then that's absolutely fine, and you can always run RepoBee with the full path to $REPOBEE_EXECUTABLE"
    echo "Do you want us to add $REPOBEE_BIN_DIR to your PATH? (y/n): "

    # careful with read, its options work differently in zsh and bash
    read confirm

    case "$confirm" in y|Y|yes|YES|yes)
            echo "Adding $REPOBEE_BIN_DIR to PATH"
            "$REPOBEE_PYTHON" -m userpath prepend "$REPOBEE_BIN_DIR" || exit 1
            echo "$REPOBEE_BIN_DIR added to PATH, please start a new shell for the changes to take effect."
            ;;
        *) echo "Not adding $REPOBEE_BIN_DIR to PATH. Please do this manually."
    esac
}

install

echo ""
echo "RepoBee was installed successfully. To uninstall, simply remove the directory at $REPOBEE_INSTALL_DIR"
echo "If you are having trouble, please visit the FAQ at https://repobee.readthedocs.io/troubleshoot.html"
