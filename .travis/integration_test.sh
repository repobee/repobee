# build RepoBee docker test container
docker build -t repobee:test -f Dockerfile.test .

# execute integration tests
cd tests/integration_tests/
export REPOBEE_NO_VERIFY_SSL='true'
pytest integration_tests.py -vv -k assign_one_review --capture=no --showlocals
