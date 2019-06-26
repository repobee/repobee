cd tests/integration_tests/
sudo docker network create development
./startup.sh
sudo docker run --name curl --rm --net development appropriate/curl -fsSl -k https://gitlab.integrationtest.local
cd -
