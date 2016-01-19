install
lang en_US.UTF-8
keyboard us
rootpw  --plaintext asdasdasd
timezone --utc America/New_York

url --url=http://dl.fedoraproject.org/pub/fedora/linux/development/$releasever/$basearch/os/

clearpart --all --initlabel
bootloader --location=mbr
part biosboot --fstype=biosboot --size=1
part /boot --fstype ext4 --size=200
part pv.1 --size=5000
part pv.2 --fstype=lvmpv --size=1 --grow
volgroup fedora pv.1
logvol swap --fstype swap --name=swap --vgname=fedora --size=500
logvol / --fstype ext4 --name=root --vgname=fedora --size=4000

# Use this with the docker command. It must be named docker-pool
volgroup docker pv.2
logvol none --name=docker-pool --vgname=docker --size=8000 --thinpool


services --enable=docker

%packages
docker
%end


# Everything after -- is passed to the docker daemon command.
%addon com_redhat_docker --vgname=docker --fstype=xfs -- -D -l debug
docker pull hello-world
docker pull busybox
docker pull training/postgres
docker images

docker create -v /dbdata --name dbdata training/postgres /bin/true
docker run -d --volumes-from dbdata --name db1 training/postgres
docker run -d --volumes-from dbdata --name db2 training/postgres
docker run -d --name db3 --volumes-from db1 training/postgres

docker ps
docker stop db1 db2 db3
%end
