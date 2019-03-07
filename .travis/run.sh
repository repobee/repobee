#!/bin/bash

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv local 3.5.4 3.6.5 3.7.0
    pyenv global 3.7.0
    tox
else
    pytest tests --cov=repomate --cov-branch
fi
