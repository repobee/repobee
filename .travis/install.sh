#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then

    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install "$PYTHON"
    pyenv global "$PYTHON"
    python -m pip install -e ".[TEST]"
else
    pip install -e ".[TEST]"
fi
