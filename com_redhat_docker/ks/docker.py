'''
Docker Anaconda Kickstart Addon
'''
#pylint: disable=line-too-long
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
from blivet.devices import BTRFSDevice

from pyanaconda.addons import AddonData
from pyanaconda.iutil import execWithRedirect, getSysroot
from pyanaconda.iutil import startProgram
from pyanaconda.kickstart import AnacondaKSScript
from pyanaconda.simpleconfig import SimpleConfigFile

from pykickstart.options import KSOptionParser
from pykickstart.errors import KickstartParseError, formatErrorMsg

from com_redhat_docker.i18n import _

import logging
log = logging.getLogger("anaconda")

__all__ = ["DockerData"]

class LVMStorage(object):
    def __init__(self, addon):
        self.addon = addon

    @property
    def dm_fs(self):
        """ Return the docker dm.fs value """
        if not self.addon:
            return ""
        return "dm.fs=%s" % self.addon.fstype

    @property
    def pool_name(self):
        """ Return the docker dm.thinpool value """
        if not self.addon:
            return ""
        return "dm.thinpooldev=/dev/mapper/%s-docker--pool" % self.addon.vgname

    @property
    def addon_str(self):
        """ Return the addon string and storage driver options """
        return '%%addon %s --vgname="%s" --fstype="%s"' % (self.addon.name, self.addon.vgname, self.addon.fstype)

    def check_setup(self, storage, ksdata, instClass):
        """ Check storage to make sure the selected VG has a thinpool and it is named docker-pool

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object

        If there is an error, raise the appropriate Kickstart error.
        """
        if self.addon.vgname not in (vg.name for vg in storage.vgs):
            raise KickstartParseError(formatErrorMsg(0, msg=_("%%addon com_redhat_docker is missing VG named %s")) % self.addon.vgname)

        # Make sure the VG has a docker-pool LV
        if self.addon.vgname+"-docker-pool" not in (lv.name for lv in storage.lvs):
            raise KickstartParseError(formatErrorMsg(0, msg=_("%%addon com_redhat_docker is missing a LV named docker-pool")))

    def docker_cmd(self, storage, ksdata, instClass, users):
        """ Return the docker command's storage arguments

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        return ["--storage-driver", "devicemapper", "--storage-opt", self.dm_fs, "--storage-opt", self.pool_name]

    def write_configs(self, storage, ksdata, instClass, users):
        """ Write configuration file(s)

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        with open(getSysroot()+"/etc/sysconfig/docker-storage", "w") as fp:
            fp.write('DOCKER_STORAGE_OPTIONS="--storage-driver devicemapper '
                     '--storage-opt %s --storage-opt %s"\n' % (self.dm_fs, self.pool_name))

        with open(getSysroot()+"/etc/sysconfig/docker-storage-setup", "a") as fp:
            fp.write("VG=%s\n" % self.addon.vgname)

    def options(self, options):
        """ Modify the docker config file OPTION value

        :param str options: docker config file OPTIONS string

            LVM doesn't modify the value.
        """
        return options

class OverlayStorage(object):
    def __init__(self, addon):
        self.addon = addon

    @property
    def addon_str(self):
        """ Return the addon string and storage driver options """
        return '%%addon %s --overlay' % self.addon.name

    def check_setup(self, storage, ksdata, instClass):
        """ Nothing to check for overlay """
        return

    def docker_cmd(self, storage, ksdata, instClass, users):
        """ Return the docker command's storage arguments

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        return ["--storage-driver", "overlay"]

    def write_configs(self, storage, ksdata, instClass, users):
        """ Write configuration file(s)

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        with open(getSysroot()+"/etc/sysconfig/docker-storage", "w") as fp:
            fp.write('DOCKER_STORAGE_OPTIONS="--storage-driver overlay"\n')

    def options(self, options):
        """ Modify the docker config file OPTION value

        :param str options: docker config file OPTIONS string

        overlayfs doesn't work with --selinux-enabled, so remove it
        """
        log.info("Removing --selinux-enabled from docker OPTIONS for overlay driver")
        return options.replace("--selinux-enabled", "")

class BTRFSStorage(object):
    def __init__(self, addon):
        self.addon = addon

    @property
    def addon_str(self):
        """ Return the addon string and storage driver options """
        return '%%addon %s --btrfs' % self.addon.name

    def check_setup(self, storage, ksdata, instClass):
        """ Check to make sure /var/lib/docker is on a BTRFS filesystem"""
        for path in ["/var/lib/docker", "/var/lib", "/var", "/"]:
            device = storage.mountpoints.get(path)
            if isinstance(device, BTRFSDevice):
                log.debug("com_redhat_docker found BTRFS at %s", path)
                return

        raise KickstartParseError(formatErrorMsg(0, msg=_("%%addon com_redhat_docker /var/lib/docker is not on a BTRFS volume")))

    def docker_cmd(self, storage, ksdata, instClass, users):
        """ Return the docker command's storage arguments

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        return ["--storage-driver", "btrfs"]

    def write_configs(self, storage, ksdata, instClass, users):
        """ Write configuration file(s)

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        with open(getSysroot()+"/etc/sysconfig/docker-storage", "w") as fp:
            fp.write('DOCKER_STORAGE_OPTIONS="--storage-driver btrfs"\n')

    def options(self, options):
        """ Modify the docker config file OPTION value

        :param str options: docker config file OPTIONS string

        BTRFS doesn't modify the OPTIONS
        """
        return options

class DockerData(AddonData):
    """Addon data for the docker configuration"""

    def __init__(self, name):
        """ :param str name: Addon name """
        log.info("Initializing docker addon")
        # Called very early in anaconda setup
        AddonData.__init__(self, name)

        # This is set to one of the storage classes in handle_header
        self.storage = None
        self.vgname = None
        self.fstype = "xfs"
        self.enabled = False
        self.extra_args = []
        self.save_args = False

    def __str__(self):
        if not self.enabled:
            return ""

        addon_str = self.storage.addon_str

        if self.save_args:
            addon_str += " --save-args"
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
        if not self.enabled:
            return

        if "docker" not in ksdata.packages.packageList:
            raise KickstartParseError(formatErrorMsg(0, msg=_("%%package section is missing docker")))

        self.storage.check_setup(storage, ksdata, instClass)

    def handle_header(self, lineno, args):
        """ Handle the kickstart addon header

        :param lineno: Line number
        :param args: arguments from %addon line
        """
        # This gets called after __init__, very early in the installation.
        op = KSOptionParser()
        op.add_option("--vgname",
                      help="Name of the VG that contains a thinpool named docker-pool")
        op.add_option("--fstype",
                      help="Type of filesystem for docker to use with the docker-pool")
        op.add_option("--overlay", action="store_true",
                      help="Use the overlay driver")
        op.add_option("--btrfs", action="store_true",
                      help="Use the BTRFS driver")
        op.add_option("--save-args", action="store_true", default=False,
                      help="Save all extra args to the OPTIONS variable in /etc/sysconfig/docker")
        (opts, extra) = op.parse_args(args=args, lineno=lineno)

        if sum(1 for v in [opts.overlay, opts.btrfs, opts.vgname] if bool(v)) != 1:
            raise KickstartParseError(formatErrorMsg(lineno,
                                                     msg=_("%%addon com_redhat_docker must choose one of --overlay, --btrfs, or --vgname")))

        self.enabled = True
        self.extra_args = extra
        self.save_args = opts.save_args

        if opts.overlay:
            self.storage = OverlayStorage(self)
        elif opts.btrfs:
            self.storage = BTRFSStorage(self)
        elif opts.vgname:
            fmt = blivet.formats.get_format(opts.fstype)
            if not fmt or fmt.type is None:
                raise KickstartParseError(formatErrorMsg(lineno,
                                                         msg=_("%%addon com_redhat_docker fstype of %s is invalid.")) % opts.fstype)

            self.vgname = opts.vgname
            self.fstype = opts.fstype
            self.storage = LVMStorage(self)

    def execute(self, storage, ksdata, instClass, users):
        """ Execute the addon

        :param storage: Blivet storage object
        :param ksdata: Kickstart data object
        :param instClass: Anaconda installclass object
        :param users: Anaconda users object
        """
        if not self.enabled:
            return

        log.info("Executing docker addon")
        # This gets called after installation, before initramfs regeneration and kickstart %post scripts.
        execWithRedirect("mount", ["-o", "bind", getSysroot()+"/var/lib/docker", "/var/lib/docker"])
        execWithRedirect("mount", ["-o", "bind", getSysroot()+"/etc/docker", "/etc/docker"])

        # Start up the docker daemon
        log.debug("Starting docker daemon")
        docker_cmd = ["docker", "daemon"]
        if ksdata.selinux.selinux:
            docker_cmd += ["--selinux-enabled"]

        # Add storage specific arguments to the command
        docker_cmd += self.storage.docker_cmd(storage, ksdata, instClass, users)

        docker_cmd += ["--ip-forward=false", "--iptables=false"]
        docker_cmd += self.extra_args
        docker_proc = startProgram(docker_cmd, stdout=open("/tmp/docker-daemon.log", "w"), reset_lang=True)

        log.debug("Running docker commands")
        script = AnacondaKSScript(self.content, inChroot=False, logfile="/tmp/docker-addon.log")
        script.run("/")

        # Kill the docker process
        log.debug("Shutting down docker daemon")
        docker_proc.kill()

        log.debug("Writing docker configs")
        self.storage.write_configs(storage, ksdata, instClass, users)

        # Rewrite the OPTIONS entry with the extra args and/or storage specific changes
        try:
            docker_cfg = SimpleConfigFile(getSysroot()+"/etc/sysconfig/docker")
            docker_cfg.read()
            options = self.storage.options(docker_cfg.get("OPTIONS"))
            if self.save_args:
                log.info("Adding extra args to docker OPTIONS")
                options += " " + " ".join(self.extra_args)
            docker_cfg.set(("OPTIONS", options))
            docker_cfg.write()
        except IOError as e:
            log.error("Error updating OPTIONS in /etc/sysconfig/docker: %s", e)

        # Copy the log files to the system
        dstdir = "/var/log/anaconda/"
        os.makedirs(dstdir, exist_ok=True)
        for l in ["docker-daemon.log", "docker-addon.log"]:
            shutil.copy2("/tmp/"+l, dstdir+l)
