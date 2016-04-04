Name:      docker-anaconda-addon
Version:   0.2
Release:   1%{?dist}
Summary:   Anaconda kickstart support for Docker

License:   GPLv2+
Url:       https://github.com/rhinstaller/docker-anaconda-addon
# Source tar.gz can be rebuilt from github repo by running:
# make po-pull
# make scratch
Source0:   docker-anaconda-addon-%{version}.tar.gz

BuildArch: noarch

BuildRequires: python3-devel
BuildRequires: gettext

Requires: anaconda-core >= 25.5
Requires: docker
Requires: docker-selinux
Requires: docker-utils

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
* Wed Feb 10 2016 Brian C. Lane <bcl@redhat.com> - 0.2-1
- Include the po/ files in the tar.gz archive (bcl)
- Update specfile with packaging corrections and lang handling (bcl)
- Change KickstartValueError to KickstartParseError (bcl)
- Remove references to the eintr pocketlint checker (dshea)

* Tue Jan 19 2016 Brian C. Lane <bcl@redhat.com> 0.1-1
- Initial creation of docker-anaconda-addon
