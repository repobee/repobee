cd tests/integration_tests/
sudo docker network create development
./startup.sh
sudo docker run --name curl --rm --net development appropriate/curl -fsSl -k -H "Private-Token: $(cat token)" https://gitlab.integrationtest.local/api/v4/projects
cd -
