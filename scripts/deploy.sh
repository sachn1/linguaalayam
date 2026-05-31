#!/bin/bash
set -e
cd /root/linguaalayam
git fetch --tags origin
git reset --hard origin/master
docker compose up --build -d app
echo "Deployed $(git describe --tags --abbrev=0)"
