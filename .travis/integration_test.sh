# build RepoBee docker test container
docker build -t repobee:test -f Dockerfile.test .

# execute integration tests
cd tests/integration_tests/
export REPOBEE_NO_VERIFY_SSL='true'
export PYTHONWARNINGS="ignore:Unverified HTTPS request"
pytest integration_tests.py -vv --showlocals
