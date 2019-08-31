# build RepoBee docker test container
sudo docker build -t repobee:test -f Dockerfile.test .

# execute integration tests
cd tests/integration_tests/
sudo docker network create development
./startup.sh > /dev/null
export REPOBEE_NO_VERIFY_SSL='true'
pytest integration_tests.py -vv -k 'Open or Close'
exit $?
