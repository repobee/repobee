#!/bin/bash

if [[ $INTEGRATION_TEST == "true" ]]; then
    ./.travis/integration_test.sh
    exit $?
fi

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    eval "$(pyenv init -)"
    pyenv global 3.6.10
fi

pytest tests/unit_tests --cov=_repobee --cov=repobee_plug --cov-branch
