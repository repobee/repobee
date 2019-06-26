# build RepoBee docker test container
sudo docker build -t repobee:test -f Dockerfile.test .

# setup virtualenv
pip install pipenv
pipenv shell
pip install -e .[TEST]

# execute integration tests
cd tests/integration_tests/
sudo docker network create development
./startup.sh
sudo python -m pytest integration_tests.py
cd -
