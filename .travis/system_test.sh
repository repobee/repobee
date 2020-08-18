# build RepoBee docker test container
docker build -t repobee:test -f Dockerfile.test .

# execute system tests
cd system_tests
export REPOBEE_NO_VERIFY_SSL='true'
export PYTHONWARNINGS="ignore:Unverified HTTPS request"
pytest test_gitlab_system.py -vv --showlocals
