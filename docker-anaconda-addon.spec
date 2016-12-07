# Disable debug package -- Exclusivearch is used to skip building on ppc64
%global debug_package %{nil}

Name:      docker-anaconda-addon
Version:   0.4
Release:   3%{?dist}
Summary:   Anaconda kickstart support for Docker

License:   GPLv2+
Url:       https://github.com/rhinstaller/docker-anaconda-addon
# Source tar.gz can be rebuilt from github repo by running:
# make po-pull
# make scratch
Source0:   docker-anaconda-addon-%{version}.tar.gz

# Docker isn't available on all of the Fedora primary arches
# See rhbz#1315903
# The list of arches comes from docker.spec
#BuildArch: noarch
ExclusiveArch: %{ix86} x86_64 %{arm} aarch64 ppc64le s390x %{mips}

BuildRequires: python3-devel
BuildRequires: gettext

Requires: anaconda-core >= 25.5
Requires: docker
Requires: docker-selinux

%description
Add a kickstart addon section to Anaconda, com_redhat_docker, to run Docker on
the newly installed system during the installation process.

%prep
%setup -q -n docker-anaconda-addon-%{version}

%build

%install
%make_install
%find_lang %{name}

%files -f %{name}.lang
%license COPYING
%doc docs/docker-anaconda-addon.rst
%doc docs/*ks
%{_datadir}/anaconda/addons/com_redhat_docker

%changelog
* Tue Dec 06 2016 Brian C. Lane <bcl@redhat.com> - 0.4-3
- Only build on arches supported by Docker (bcl)

* Fri Jun 24 2016 Brian C. Lane <bcl@redhat.com> - 0.4-1
- Make it easier to override PYTHONPATH (bcl)
- Drop docker-utils requirement, the subpackage has been removed from docker (bcl)
- Add support for new Anaconda addon methods (#1288636) (jkonecny)

* Wed Jun 22 2016 Brian C. Lane <bcl@redhat.com> - 0.3-2
- Drop docker-utils requirement, the subpackage has been removed from docker

* Mon Apr 04 2016 Brian C. Lane <bcl@redhat.com> - 0.3-1
- Bump anaconda minimum version to 25.5 for Blivet API changes (bcl)
- Adapt to blivet-2.0 API. (dlehman)
- Add link to documentation on github.io (bcl)

* Wed Feb 10 2016 Brian C. Lane <bcl@redhat.com> - 0.2-1
- Include the po/ files in the tar.gz archive (bcl)
- Update specfile with packaging corrections and lang handling (bcl)
- Change KickstartValueError to KickstartParseError (bcl)
- Remove references to the eintr pocketlint checker (dshea)

* Tue Jan 19 2016 Brian C. Lane <bcl@redhat.com> 0.1-1
- Initial creation of docker-anaconda-addon
