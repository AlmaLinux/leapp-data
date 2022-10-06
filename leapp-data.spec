%define dist_list almalinux centos eurolinux oraclelinux rocky
%define conflict_dists() %(for i in almalinux centos eurolinux oraclelinux rocky; do if [ "${i}" != "%{dist_name}" ]; then echo -n "leapp-data-${i} "; fi; done)

Name:		leapp-data-%{dist_name}
Version:	0.2
Release:	2%{?dist}
Summary:	data for migrating tool
Group:		Applications/Databases
License:	ASL 2.0
URL:		https://github.com/AlmaLinux/leapp-data
Source0:	leapp-data-%{version}.tar.gz
BuildArch:  noarch

Conflicts: %{conflict_dists}

%description
%{dist_name} %{summary}


%prep
%setup -q


%build


%install
mkdir -p %{buildroot}%{_sysconfdir}/leapp/files/vendors.d
install -t %{buildroot}%{_sysconfdir}/leapp/files files/%{dist_name}/*
install -t %{buildroot}%{_sysconfdir}/leapp/files/vendors.d vendors.d/*

%if 0%{?rhel} == 7
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el8 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el8 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el9
%endif
%if 0%{?rhel} == 8
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el9 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el9 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el8
%endif


%files
%doc LICENSE NOTICE README.md
%{_sysconfdir}/leapp/files/*


%changelog
* Fri Sep 30 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-2
- Split repomap.json

* Fri Sep 30 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-1
- Add 8 to 9 migration support for AlmaLinux

* Thu Sep 1 2022 Roman Prilipskii <rprilpskii@cloudlinux.com> - 0.1-7
- made third-party files accessible for all supported distributions

* Wed Aug 17 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.1-6
- added repomap.json file for all distributions

* Thu Mar 24 2022 Tomasz Podsiadły <tp@euro-linux.com> - 0.1-5
- Add EuroLinux to supported distributions

* Wed Mar 23 2022 Andrew Lukoshko <alukoshko@almalinux.org> - 0.1-4
- added ResilientStorage and updated repo URLs for AlmaLinux and Rocky

* Thu Oct 21 2021 Andrew Lukoshko <alukoshko@almalinux.org> - 0.1-3
- updated PES data for Oracle and Rocky

* Thu Aug 26 2021 Avi Miller <avi.miller@oracle.com> - 0.1-2
- switched to using the full oraclelinux name
- switched the Oracle Linux repos to use https
- added Apache-2.0 NOTICE attribution file

* Wed Aug 25 2021 Sergey Fokin <sfokin@almalinux.org> - 0.1-1
- initial project
