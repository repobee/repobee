# build RepoBee docker test container
sudo docker build -t repobee:test -f Dockerfile.test .

# execute integration tests
cd tests/integration_tests/
sudo docker network create development
./startup.sh > /dev/null
export REPOBEE_NO_VERIFY_SSL='true'
pytest integration_tests.py -v -k AssignReviews
if [ $? != 0 ];
then
    exit $?;
fi

cat .coverage_files/report.txt

ci_env=`bash <(curl -s https://codecov.io/env)`
docker run $ci_env \
    -v .coverage_files:/coverage \
    --net development --rm \
    --name repobee \
    repobee:test /bin/sh -c 'cd /coverage && codecov'
