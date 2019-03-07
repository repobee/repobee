#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then

    brew upgrade pyenv
    eval "$(pyenv init -)"
    pyenv install 3.5.4 --skip-existing
    pyenv install 3.6.5 --skip-existing
    pyenv install 3.7.0 --skip-existing
    pyenv global 3.7.0
    pip install pip --upgrade
    pip install tox tox-pyenv
else
    pip install -e ".[TEST]"
fi
