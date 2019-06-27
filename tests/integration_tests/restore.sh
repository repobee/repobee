status="$(sudo docker inspect -f {{.State.Health.Status}} gitlab)"
while [ "$status" != "healthy" ]; do 

    if [ "$status" == "unhealthy" ]; then
        exit 1
    fi

    sleep 10
    status="$(sudo docker inspect -f {{.State.Health.Status}} gitlab)"
    echo "GitLab status: ${status} ..."
done
echo "Gitlab has started!"
sudo docker exec -t gitlab chown git:git /var/opt/gitlab/backups/test_gitlab_backup.tar
sudo docker exec -t gitlab gitlab-rake gitlab:backup:restore force=yes
sudo docker exec -t gitlab gitlab-ctl reconfigure
