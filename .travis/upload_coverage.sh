#!/bin/bash

cd system_tests
rm -f .coverage_files/.coverage
codecov --file .coverage_files/coverage.xml
