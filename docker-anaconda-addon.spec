Name:      docker-anaconda-addon
Version:   0.1
Release:   1%{?dist}
Summary:   Anaconda kickstart support for Docker

License:   GPLv2+
Url:       https://github.com/rhinstaller/docker-anaconda-addon
Source0:   https://github.com/rhinstaller/docker-anaconda-addon/archive/%{version}/docker-anaconda-addon-%{version}.tar.gz

BuildArch: noarch

BuildRequires: python3-devel
BuildRequires: python3-pylint
BuildRequires: gettext

Requires: anaconda-core >= 24.0
Requires: python3-polib
Requires: python3-pylint
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

%files
%license COPYING
%doc docs/docker-anaconda-addon.rst
%doc docs/*ks
%{_datadir}/anaconda/addons/com_redhat_docker

%changelog
* Tue Jan 19 2016 Brian C. Lane <bcl@redhat.com> 0.1-1
- Initial creation of docker-anaconda-addon
