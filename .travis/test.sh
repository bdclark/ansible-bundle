#!/bin/bash
set -e

die() {
   [[ -n "$1" ]] && >&2 echo "Error: $1"
   exit 1
}

[[ -n "$IMAGE" ]] || die "IMAGE required"
[[ -n "$DOCKERFILE" ]] || die "DOCKERFILE required"
[[ -n "$ANSIBLE_VERSION" ]] || die "ANSIBLE_VERSION required"

echo "ANSIBLE_VERSION=$ANSIBLE_VERSION"
echo "DOCKERFILE=$DOCKERFILE"
echo "IMAGE=$IMAGE"
exit 0

docker build -t "local/$IMAGE" -f ".travis/$DOCKERFILE" --build-arg "IMAGE=$IMAGE" .
docker run -d --name installer -v "$(pwd)/build:/build" "local/$IMAGE"
docker exec installer unzip "/build/ansible-bundle-$ANSIBLE_VERSION.zip"
docker exec installer python2 ./ansible-bundle/install -i /opt/ansible-py2
docker exec installer python3 ./ansible-bundle/install -i /opt/ansible-py3 -l /usr/local/bin
docker exec installer ls -al /usr/local/bin
docker exec installer /opt/ansible-py2/bin/ansible --version
docker exec installer /usr/local/bin/ansible --version
