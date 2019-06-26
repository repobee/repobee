sudo docker-compose up -d
sudo docker exec -it gitlab update-permissions
sudo docker container stop gitlab
sudo docker-compose up -d
./restore.sh
