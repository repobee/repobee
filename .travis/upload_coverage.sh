#!/bin/bash

if [[ $SYSTEM_TEST == "true" ]];
then
    cd tests/integration_tests
    rm -f .coverage_files/.coverage
    codecov --file .coverage_files/coverage.xml
else
    codecov
fi
