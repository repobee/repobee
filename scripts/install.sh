#! /bin/bash

set -o errexit
set -o nounset

REPOBEE_INSTALL_DIR=${REPOBEE_INSTALL_DIR:-"$HOME/.repobee"}
REPOBEE_INSTALL_NONINTERACTIVE=${REPOBEE_INSTALL_NONINTERACTIVE:-"false"}

echo "Using install dir '$REPOBEE_INSTALL_DIR'"
REPOBEE_BIN_DIR="$REPOBEE_INSTALL_DIR/bin"
REPOBEE_REPO_DIR="$REPOBEE_INSTALL_DIR/repobee_git"
REPOBEE_HTTPS_URL="https://github.com/repobee/repobee"
REPOBEE_EXECUTABLE="$REPOBEE_BIN_DIR/repobee"
REPOBEE_INSTALLED_PLUGINS="$REPOBEE_INSTALL_DIR/installed_plugins.json"

VENV_DIR="$REPOBEE_INSTALL_DIR/env"
REPOBEE_PIP="$VENV_DIR/bin/pip"
REPOBEE_ENV_ACTIVATE="$VENV_DIR/bin/activate"
REPOBEE_PYTHON="$VENV_DIR/bin/python"

# tab completion stuff
REPOBEE_COMPLETION="$REPOBEE_INSTALL_DIR/completion"
REPOBEE_BASH_COMPLETION="$REPOBEE_COMPLETION/bash_completion.sh"
REGISTER_PYTHON_ARGCOMPLETE="$REPOBEE_INSTALL_DIR/env/bin/register-python-argcomplete"

MIN_PYTHON_VERSION=8

function install() {
    repobee_pip_uri=$1

    if [ -d "$REPOBEE_INSTALL_DIR" ]; then
        echo "Found RepoBee installation at $REPOBEE_INSTALL_DIR, attempting repair and upgrade ..."
    fi

    check_prerequisites
    install_repobee "$repobee_pip_uri"
}

function check_prerequisites() {
    # check that Python 3.8+, pip and Git are installed
    installed_python=$(find_python)
    if [ -z "$installed_python" ]; then
        printf "\nCannot find any compatible version of Python installed.\n"
        echo "Please install Python 3.8 or higher and then rerun this script."
        echo "See https://www.python.org/downloads/ for a Python installer."
        exit 1
    else
        echo "Found appropriate Python executable: $installed_python"
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
    repobee_pip_uri="$1"
    echo "Installing RepoBee at $REPOBEE_INSTALL_DIR"

    # virtualenv works better in CI as it properly copies pip from another
    # virtualenv while venv doesn't appear to do that. So we try both.
    $(find_python) -m virtualenv "$VENV_DIR" &> /dev/null || $(find_python) -m venv "$VENV_DIR" &> /dev/null || {
        printf "\nFailed to create a virtual environment for RepoBee.\n"
        echo "This is typically caused by the venv package not being installed."
        printf "If you run Ubuntu/Debian, try running the following commands:\n\n"
        echo "    sudo apt-add-repository universe"
        echo "    sudo apt update"
        echo "    sudo apt install python3-venv"
        printf "\nThen re-execute this script."
        exit 1
    }

    source "$REPOBEE_ENV_ACTIVATE"
    ensure_pip_installed

    echo "Installing RepoBee $repobee_pip_uri"
    REPOBEE_INSTALL_DIR="$REPOBEE_INSTALL_DIR" pip_install_quiet_failfast "$repobee_pip_uri"
    create_repobee_executable

    # we intentionally clobber the installed plugins file to fix installations
    # broken by failing or missing plugins
    echo "{}" > "$REPOBEE_INSTALLED_PLUGINS"

    echo "Checking PATH"
    pip_install_quiet_failfast userpath
    python -m userpath verify "$REPOBEE_BIN_DIR" &> /dev/null \
    && echo "PATH OK" || add_to_path
}

function find_python() {
    # Find an appropriate python executable
    for exec_suffix in "3.11" "3.10" "3.9" "3.8" "3" ""; do
        python_exec="python$exec_suffix"
        minor_version=$(get_minor_python3_version "$python_exec")
        if [ "$minor_version" -ge "$MIN_PYTHON_VERSION" ]; then
            echo "$python_exec"
            return
        fi
    done
}

function get_minor_python3_version() {
    # echo the minor version number from the given Python executable, or -1 if
    # the executable does not exist or is not Python 3
    python_executable=$1
    if ! "$python_executable" -V &> /dev/null; then
        echo -1
        return
    fi

    # python2 prints the version on stderr, hence the 2>&1 redirect
    major=$("$python_executable" 2>&1 -V | grep -o '[0-9]\+' | sed -n 1p)
    minor=$("$python_executable" 2>&1 -V | grep -o '[0-9]\+' | sed -n 2p)

    if [ "$major" -ne 3 ]; then
        echo -1
        return
    fi
    echo "$minor"
}

function pip_install_quiet_failfast() {
    "$REPOBEE_PIP" install --upgrade $1 > /dev/null || {
        echo "There was a problem installing $1"
        exit 1
    }
}

function ensure_pip_installed() {
    "$REPOBEE_PIP" install --upgrade pip &> /dev/null || {
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
    ln -sf "$VENV_DIR/bin/repobee" "$REPOBEE_EXECUTABLE"

    echo "RepoBee exuctable created at $REPOBEE_EXECUTABLE"
}

function add_to_path() {
    if [ "$REPOBEE_INSTALL_NONINTERACTIVE" = true ]; then
        echo "Non-interactive mode, skipping PATH modification"
        return
    fi

    printf "\n$REPOBEE_BIN_DIR is not on the PATH, so to run RepoBee you must type the full path to $REPOBEE_EXECUTABLE.\n"
    echo "We can add try to add $REPOBEE_BIN_DIR to your PATH by adding it to your profile files (e.g. .bashrc, .zshrc, config.fish, etc), and then you just need to type 'repobee' to run it."
    echo "If you know how to do this manually, then we recommend that you do so such that you get it the way you like it."
    echo "Do you want us to try to add $REPOBEE_BIN_DIR to your PATH? [y/N]: "

    # careful with read, its options work differently in zsh and bash
    read confirm

    case "$confirm" in y|Y|yes|YES|yes)
            echo "Adding $REPOBEE_BIN_DIR to PATH"
            "$REPOBEE_PYTHON" -m userpath append "$REPOBEE_BIN_DIR" || exit 1
            echo "$REPOBEE_BIN_DIR added to PATH, please start a new shell for the changes to take effect."
            ;;
        *) echo "Not adding $REPOBEE_BIN_DIR to PATH. Please do this manually."
    esac
}

function get_latest_version() {
    curl --version &> /dev/null || {
        echo "Running this install script without specifying a version requires curl."
        echo "Please install curl or manually specify a version to install."
        echo "You can find the latest version here: https://github.com/repobee/repobee/releases/latest"
    }

    # find the version number of the latest release of RepoBee
    echo $(curl -Ls -o /dev/null -w %{url_effective} https://github.com/repobee/repobee/releases/latest | awk -F / '{ print $NF }')
}

function create_autocomplete_scripts() {
    mkdir -p "$REPOBEE_COMPLETION"

echo "# Tab completion for bash/zsh
$($REGISTER_PYTHON_ARGCOMPLETE repobee)
" > "$REPOBEE_BASH_COMPLETION"
}

function auto_complete_msg() {
    echo "
### TAB COMPLETION INSTRUCTIONS ###

To enable tab completion, see https://docs.repobee.org/en/stable/install.html#tab-completion

###################################
"
}

function resolve_repobee_pip_uri() {
    # the optional argument can be either a version tag, or a local filepath
    version="${1:-}"
    if [ "$version" ]; then
        if [ -d "$version" ]; then
            repobee_pip_uri="$version"
        else
            repobee_pip_uri="git+$REPOBEE_HTTPS_URL.git@$version"
        fi
    else
        repobee_pip_uri="repobee==$(get_latest_version)"
    fi
    echo "$repobee_pip_uri"
}

function main() {
    version="${1:-}"
    install "$(resolve_repobee_pip_uri $version)"
    create_autocomplete_scripts
    auto_complete_msg

    echo "
RepoBee was installed successfully. To uninstall, simply remove the directory at $REPOBEE_INSTALL_DIR
If you are having trouble, please visit the FAQ at https://repobee.readthedocs.io/en/stable/faq.html
    "
}

main "${1:-}"
