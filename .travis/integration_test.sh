# set the domain
sudo echo "127.0.2.1       gitlab.integrationtest.local   gitlab" >> /etc/hosts
./tests/integration_tests/startup.sh
curl -k https://gitlab.integrationtest.local
