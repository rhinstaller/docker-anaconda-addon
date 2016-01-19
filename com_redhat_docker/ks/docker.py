# Docker Anaconda Kickstart Addon
#
# Copyright (C) 2016 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): Brian C. Lane <bcl@redhat.com>
#
import os
import shutil
import blivet.formats

from pyanaconda.addons import AddonData
from pyanaconda.iutil import execWithRedirect, getSysroot
from pyanaconda.iutil import startProgram
from pyanaconda.kickstart import AnacondaKSScript

from pykickstart.options import KSOptionParser
from pykickstart.errors import KickstartValueError, formatErrorMsg

from com_redhat_docker.i18n import _

import logging
log = logging.getLogger("anaconda")

__all__ = ["DockerData"]

# pylint: disable=interruptible-system-call

class DockerData(AddonData):
    """Addon data for the docker configuration"""

    def __init__(self, name):
        """ :param str name: Addon name """
        log.info("Initializing docker addon")
        # Called very early in anaconda setup
        AddonData.__init__(self, name)
        self.vgname = "docker"
        self.fstype = "xfs"
        self.enabled = False
        self.extra_args = []

    def __str__(self):
        if not self.enabled:
            return ""

        addon_str = '%%addon %s --vgname="%s" --fstype="%s"' % (self.name, self.vgname, self.fstype)
        if self.extra_args:
            addon_str += " -- %s" % " ".join(self.extra_args)
        addon_str += "\n%s\n%%end\n" % self.content.strip()

        return addon_str

    def setup(self, storage, ksdata, instClass):
        """ Setup the addon

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        """
        # This gets called after entering progress hub, just before installation and device partitioning.

        if "docker" not in ksdata.packages.packageList:
            raise KickstartValueError(formatErrorMsg(0, msg=_("%%package section is missing docker")))

        # Check storage to make sure the selected VG has a thinpool and it is named docker-pool?
        if self.vgname not in (vg.name for vg in storage.vgs):
            raise KickstartValueError(formatErrorMsg(0, msg=_("%%addon com_redhat_docker is missing VG named %s")) % self.vgname)

        # Make sure the VG has a docker-pool LV
        if self.vgname+"-docker-pool" not in (lv.name for lv in storage.lvs):
            raise KickstartValueError(formatErrorMsg(0, msg=_("%%addon com_redhat_docker is missing a LV named docker-pool")))

    def handle_header(self, lineno, args):
        """ Handle the kickstart addon header

        :param lineno: Line number
        :param args: arguments from %addon line
        """
        # This gets called after __init__, very early in the installation.
        op = KSOptionParser()
        op.add_option("--vgname", required=True,
                      help="Name of the VG that contains a thinpool named docker-pool")
        op.add_option("--fstype", required=True,
                      help="Type of filesystem to use for docker to use with docker-pool")
        (opts, extra) = op.parse_args(args=args, lineno=lineno)

        fmt = blivet.formats.getFormat(opts.fstype)
        if not fmt or fmt.type is None:
            raise KickstartValueError(formatErrorMsg(lineno,
                                      msg=_("%%addon com_redhat_docker fstype of %s is invalid.")) % opts.fstype)

        self.vgname = opts.vgname
        self.fstype = opts.fstype
        self.enabled = True
        self.extra_args = extra

    def execute(self, storage, ksdata, instClass, users):
        """ Execute the addon

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        log.info("Executing docker addon")
        # This gets called after installation, before initramfs regeneration and kickstart %post scripts.
        execWithRedirect("mount", ["-o", "bind", getSysroot()+"/var/lib/docker", "/var/lib/docker"])
        execWithRedirect("mount", ["-o", "bind", getSysroot()+"/etc/docker", "/etc/docker"])

        # Start up the docker daemon
        log.debug("Starting docker daemon")
        dm_fs = "dm.fs=%s" % self.fstype
        pool_name = "dm.thinpooldev=/dev/mapper/%s-docker--pool" % self.vgname
        docker_cmd = ["docker", "daemon"]
        if ksdata.selinux.selinux:
            docker_cmd += ["--selinux-enabled"]
        docker_cmd += ["--storage-driver", "devicemapper",
                      "--storage-opt", dm_fs,
                      "--storage-opt", pool_name, "--ip-forward=false", "--iptables=false"]
        docker_cmd += self.extra_args
        docker_proc = startProgram(docker_cmd, stdout=open("/tmp/docker-daemon.log", "w"), reset_lang=True)

        log.debug("Running docker commands")
        script = AnacondaKSScript(self.content, inChroot=False, logfile="/tmp/docker-addon.log")
        script.run("/")

        # Kill the docker process
        log.debug("Shutting down docker daemon")
        docker_proc.kill()

        log.debug("Writing docker configs")
        with open(getSysroot()+"/etc/sysconfig/docker-storage", "w") as fp:
            fp.write('DOCKER_STORAGE_OPTIONS="--storage-driver devicemapper '
                     '--storage-opt %s --storage-opt %s"\n' % (dm_fs, pool_name))

        with open(getSysroot()+"/etc/sysconfig/docker-storage-setup", "a") as fp:
            fp.write("VG=%s\n" % self.vgname)

        # Copy the log files to the system
        dstdir = "/var/log/anaconda/"
        os.makedirs(dstdir, exist_ok=True)
        for l in ["docker-daemon.log", "docker-addon.log"]:
            shutil.copy2("/tmp/"+l, dstdir+l)
