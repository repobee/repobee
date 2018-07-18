#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then

    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install "$PYTHON"
    pyenv global "$PYTHON"
    python -m pip install -r requirements.test.txt && pip install -e .
else
    pip install -r requirements.test.txt && pip install -e .
fi
