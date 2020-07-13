#!/bin/bash
if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    brew update --force
    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install 3.6.10 --skip-existing
    pyenv global 3.6.10
    pip install pip --upgrade
fi

pip install -e ".[TEST]"
