#!/bin/bash
set -ex

die() {
   [[ -n "$1" ]] && >&2 echo "Error: $1"
   exit 1
}

[[ -n "$IMAGE" ]] || die "IMAGE required"
[[ -n "$DOCKERFILE" ]] || die "DOCKERFILE required"
[[ -n "$ANSIBLE_VERSION" ]] || die "ANSIBLE_VERSION required"
[[ -n "$ARTIFACT" ]] || die "ARTIFACT required"

docker build -t "local/$IMAGE" -f ".travis/$DOCKERFILE" --build-arg "IMAGE=$IMAGE" .
docker run -d --name installer -v "$(pwd)/build:/build" "local/$IMAGE"
docker exec installer tar xzf "/build/$ARTIFACT"

docker exec installer python2 --version
docker exec installer python2 ./ansible-bundle/install -i /opt/ansible-py2 -l /usr/local/bin
docker exec installer ls -al /usr/local/bin
docker exec installer /usr/local/bin/ansible --version

docker exec installer python3 --version
if [ "$(docker exec installer python3 -c 'import sys; print(sys.version_info.minor)')" -gt "4" ]; then
  docker exec installer python3 ./ansible-bundle/install -i /opt/ansible-py3
  docker exec installer /opt/ansible-py3/bin/ansible --version
else
  echo "Not testing for Python3 since it appears to be an incompatible version"
fi
