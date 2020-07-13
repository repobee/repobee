# build RepoBee docker test container
docker build -t repobee:test -f Dockerfile.test .

# execute integration tests
cd tests/integration_tests/
export REPOBEE_NO_VERIFY_SSL='true'


if [[ $MODULE_SET == 1 ]]; then
    pytest clone_integration_tests.py setup_integration_tests.py -vv
elif [[ $MODULE_SET == 2 ]]; then
    pytest review_integration_tests.py update_integration_tests.py -vv
elif [[ $MODULE_SET == 3 ]]; then
    pytest migrate_integration_tests.py issue_integration_tests.py -vv
fi
