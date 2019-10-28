#!/bin/bash

if [[ $INTEGRATION_TEST == "true" ]];
then
    cat .coverage_files/report.txt
    rm -f .coverage_files/.coverage
    codecov --file .coverage_files/coverage.xml
else
    codecov
fi
