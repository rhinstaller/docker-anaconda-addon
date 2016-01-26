Docker Anaconda addon
=====================

:Authors:
    Brian C. Lane <bcl@redhat.com>

This addon adds a kickstart %addon section named ``com_redhat_docker`` to
Anaconda that allows the user to run docker on their newly installed system
before rebooting.  There is no GUI or TUI interface for this, everything is
done via the kickstart.

In order to use this addon you need an Anaconda boot.iso that has been built with
the addon and a kickstart with the ``%addon com_redhat_docker`` section.

The Kickstart
-------------

The kickstart needs to setup the storage, include docker in the installation,
and run whatever docker commands are needed to install and configure images. It
should stop any running containers before the end of the section.

Storage
~~~~~~~

There are 2 options for storage, LVM thin-pool and OverlayFS. OverlayFS is
simpler, using the host filesystem from ``/var/lib/docker/`` but it doesn't
support selinux inside the containers. Pass ``--overlay`` to the addon to
enable it.

The other option is a LVM thin-pool named 'docker-pool', the VG used
can be anything, but the VG name needs to be passed to the addon with the
``--vgname`` argument. The storage setup will be verified and then the docker
daemon will be started.

eg.::

    part pv.2 --fstype=lvmpv --size=1 --grow
    volgroup docker pv.2
    logvol none --name=docker-pool --vgname=docker --size=8000 --thinpool

Addon Section
~~~~~~~~~~~~~

The addon command arguments depend on whether you are using OverlayFS or LVM.
OverlayFS is simply ``--overlay``, which will also remove ``--selinux-enabled``
from the ``/etc/sysconfig/docker`` OPTIONS variable if it is present because
the overlay doesn't support selinux inside the containers.

When using LVM it requires ``--vgname=VGNAME`` to specify the name of the VG
containing a LV thin-pool named docker-pool. Optionally you can add
``--fstype=FSNAME`` to specify the filesystem type to use with the pool. eg.
xfs, ext4. The default is xfs. You can pass any other arguments to the docker
daemon command by adding them to the end of the addon command, after ``--``,
like this::

    %addon com_redhat_docker --vgname=docker --fstype=xfs -- --add-registry docker.foo.bar

Commands inside the addon section are run as a bash shell in the installer
environment (just like a ``%post --nochroot``) so that it is flexible enough to
accomplish whatever other setup is needed. The new system is mounted at
/mnt/sysimage in this environment.

Logs are written to docker-daemon.log and docker-addon.log in /tmp/, and are
copied into /var/log/anaconda/ on the installed system.

eg.::

    %addon com_redhat_docker --vgname=docker --fstype=xfs
    docker pull hello-world
    docker pull busybox
    docker images
    %end

.. NOTE::

    The extra arguments are normally only used during installation. If they should
    be used after reboot add ``--save-args`` before the ``--``.

Example
~~~~~~~

You can add support to an existing kickstart by doing something similar to this::

    part pv.2 --fstype=lvmpv --size=1 --grow
    volgroup docker pv.2
    logvol none --name=docker-pool --vgname=docker --size=8000 --thinpool

    services --enable=docker

    %packages
    docker
    %end

    %addon com_redhat_docker --vgname=docker --fstype=xfs
    docker pull hello-world
    docker pull busybox
    docker images
    %end
