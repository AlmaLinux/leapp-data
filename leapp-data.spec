%global pes_events_build_date 20240827

%define dist_list almalinux centos eurolinux oraclelinux rocky
%define conflict_dists() %(for i in almalinux centos eurolinux oraclelinux rocky; do if [ "${i}" != "%{dist_name}" ]; then echo -n "leapp-data-${i} "; fi; done)

%if 0%{?rhel} == 7
%define supported_vendors epel imunify kernelcare mariadb nginx-stable nginx-mainline postgresql docker-ce microsoft imunify360-alt-php
%define target_version 8
%if %{dist_name} == "almalinux"
%define gpg_key RPM-GPG-KEY-AlmaLinux-8
%endif
%if %{dist_name} == "centos"
%define gpg_key RPM-GPG-KEY-CentOS-Official
%endif
%if %{dist_name} == "eurolinux"
%define gpg_key RPM-GPG-KEY-eurolinux8
%endif
%if %{dist_name} == "oraclelinux"
%define gpg_key RPM-GPG-KEY-oracle-ol8
%endif
%if %{dist_name} == "rocky"
%define gpg_key RPM-GPG-KEY-Rocky-8
%endif
%endif
%if 0%{?rhel} == 8
%define supported_vendors epel kernelcare mariadb nginx-stable nginx-mainline postgresql docker-ce microsoft
%define target_version 9
%if %{dist_name} == "almalinux"
%define gpg_key RPM-GPG-KEY-AlmaLinux-9
%endif
%if %{dist_name} == "centos"
%define gpg_key RPM-GPG-KEY-CentOS-Official RPM-GPG-KEY-CentOS-SIG-Extras
%endif
%if %{dist_name} == "eurolinux"
%define gpg_key RPM-GPG-KEY-eurolinux9
%endif
%if %{dist_name} == "oraclelinux"
%define gpg_key RPM-GPG-KEY-oracle-ol9
%endif
%if %{dist_name} == "rocky"
%define gpg_key RPM-GPG-KEY-Rocky-9
%endif
%endif

%bcond_without check

Name:		leapp-data-%{dist_name}
Version:	0.4
Release:	11%{?dist}.%{pes_events_build_date}
Summary:	data for migrating tool
Group:		Applications/Databases
License:	ASL 2.0
URL:		https://github.com/AlmaLinux/leapp-data
Source0:	leapp-data-%{version}.tar.gz
BuildArch:  noarch

Conflicts: %{conflict_dists}

%if %{with check}
%if 0%{?rhel} == 7
BuildRequires: python36
BuildRequires: python36-jsonschema
%endif
%if 0%{?rhel} == 8
BuildRequires: python3
BuildRequires: python3-jsonschema
%endif
%endif

%description
%{dist_name} %{summary}


%prep
%setup -q


%build
sh tools/generate_map_pes_files.sh "%{dist_name}" "%{?rhel}"


%install
# Third-party repositories part
mkdir -p %{buildroot}%{_sysconfdir}/leapp/files/vendors.d
cp -rf vendors.d/* %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/
if [ "%{dist_name}" != "almalinux" ]; then
    rm -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/epel*
fi
for vendor in %{supported_vendors}; do
      [ -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/${vendor}.repo.el%{target_version} ] && \
      mv -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/${vendor}.repo.el%{target_version} \
      %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/${vendor}.repo

      [ -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/rpm-gpg/${vendor}.gpg.el%{target_version} ] && \
      mv -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/rpm-gpg/${vendor}.gpg.el%{target_version} \
      %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/rpm-gpg/${vendor}.gpg

      [ -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/${vendor}_map.json.el%{target_version} ] && \
      mv -f %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/${vendor}_map.json.el%{target_version} \
      %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/${vendor}_map.json
done
find %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/ -name \*.el\? -a ! -name \*.el%{target_version} -delete


# Main part
cp -rf files/%{dist_name}/* %{buildroot}%{_sysconfdir}/leapp/files/

rm -f %{buildroot}%{_sysconfdir}/leapp/files/config.json

%if 0%{?rhel} == 7
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el8 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el8 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el9
mkdir -p %{buildroot}%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/rpm-gpg/8/
for key in %{gpg_key}; do
    mv -f files/rpm-gpg/${key} %{buildroot}%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/rpm-gpg/8/
done
%endif
%if 0%{?rhel} == 8
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el9 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el9 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el8
mkdir -p %{buildroot}%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/rpm-gpg/9/
for key in %{gpg_key}; do
    mv -f files/rpm-gpg/${key} %{buildroot}%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/rpm-gpg/9/
done
%endif

%check
%if %{with check}
JSON_FILES=$(find %{buildroot}%{_sysconfdir}/leapp/ -path "./tests" -prune -o -name "*pes*.json*" -print0 | xargs -0 echo)

python3 tests/validate_json.py tests/pes-events-schema.json $JSON_FILES
python3 tests/validate_ids.py $JSON_FILES
python3 tests/check_debranding.py %{buildroot}%{_sysconfdir}/leapp/files/pes-events.json
%endif


%files
%doc LICENSE NOTICE README.md
%if 0%{?rhel} == 8
%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/rpm-gpg/9/
%endif

%if 0%{?rhel} == 7
%{_sysconfdir}/leapp/repos.d/system_upgrade/common/files/rpm-gpg/8/
%endif
%{_sysconfdir}/leapp/files/*


%changelog
* Mon Oct 14 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-11.20240827
- Support elevation on machines other than x86_64 with adding relevant architectures into map files
- Back kernelcare vendor support for upgrades from 8 to 9

* Thu Oct 10 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-10.20240827
- Add CentOS 7 ELS repos support for upgrades to OracleLinux

* Mon Oct 07 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-8.20240827
 - Change major release number into $releasever in AlmaLinux repositories configuration

* Fri Sep 27 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-7.20240827
 - Replace libunwind package if imunify360 vendor is enabled
 - Move GeoIP package if epel vendor is enabled
 - Add new vendor, imunify360-alt-php - CloudLinux Imunify360 alt-php packages
 - Remove unnecessery openssl-libs package split

* Fri Sep 06 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-6.20240827
- Switch CentOS Stream9 repositories from mirrorlist into baseurl at mirror.stream.centos.org

* Tue Sep 03 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-5.20240827
- Add new vendor, microsoft - Microsoft prod repository ELevation

* Tue Sep 03 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-4.20240827
- Revert "Temporary force 9.3 version due to RHEL-36249"

* Mon Sep 02 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-3.20240827
- Add new vendor, docker-ce - the open-source application container engine

* Tue Aug 27 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-2.20240827
- Update data to the upstream most recent state
 - Update pes-events.json to the state as of a757c6d0c269008ba7688c4273899dd53ca31756

- tests/check_debranding.py
 - add "redhat-indexhtml" and "redhat-display-vf-fonts" to the excludes

- Fix duplicate ids, set_ids across pes files

- tools/generate_epel_files.sh
 - Avoid risk factor (high): Packages from unknown repositories may not be installed

* Thu Aug 22 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-1.20240812
- switch repository mapping into version_format 1.2.1

* Mon Aug 12 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.3-1.20240812
- Update pes-events.json to the state as of f871cb8634ac238360adb12894aa0b7421779f38
- Fix duplicate ids, set_ids across pes files
- Bump the package pes_events_build_date, version and release: 0.3-1.20240812

- files/*/config.json
 - add "major_version": 10
 - add "rhel10-BaseOS" and "rhel10-CRB" to the "repository_replacing" (except oraclelinux)
 - add "rhel8-ceph5" and "rhel9-ceph5" to the "removable_repositories". In case of araclelinux add as well "rhel10-AppStream", "rhel10-BaseOS", "rhel10-CRB"

- tests/check_debranding.py
 - add "rhel-net-naming-sysattrs", "redhat-text-vf-fonts" and "redhat-mono-vf-fonts" to the excludes

* Wed Jul 24 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-15.20230823
- Add device driver deprecation data for all distros
- Update the data for AlmaLinux with devices which support were added in its specific release (as of 20240724090818)

* Tue Jul 16 2024 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-14.20230823
- Add CentOS 7 ELS repos support for upgrades to AlmaLinux
 
* Mon Jul 1 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-13.20230823
- Define 'supported_vendors' and 'target_version' to simplify data management for specific version
- Support of MariaDB verndors data for both EL8 and EL9
- Support of Nginx (stable) verndors data for both EL8 and EL9
- Support of Nginx (mainline) verndors data for both EL8 and EL9
- Support of PostgreSQL verndors data for both EL8 and EL9
- Support of CloudLinux Imunify360 verndors data for both EL8 and EL9
- Support of CloudLinux kernelcare verndors data for both EL8 and EL9

* Wed Jun 26 2024 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-12.2.20230823
- Do not use mirrorlist for Rocky 9.3

* Mon Jun 24 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-12.1.20230823
- Configure MariaDB repository to use version 11

* Thu Jun 20 2024 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-12.20230823
- Temporary force 9.3 version due to RHEL-36249

* Thu May 16 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-11.20230823
- Data to support upgrade of Scientific Linux 7 to AlmaLinux 8.

* Mon Apr 22 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-10.20230823
- CentOS Stream elevation:
 - add pesid for 'rt' and 'nfv' repositories (into repomap.json.el9)
 - switch 'centos9-extras' repository into the SIG (leapp_upgrade_repositories.repo.el9)
 - add RPM-GPG-KEY-CentOS-SIG-Extras key for the 'centos9-extras' repository

- ELevate EL release 8 to 9 (all distros)
 - remove the folloving packages during CS8 to CS9 migration (via pes-events.json): nautilus-sendto libdmapsharing iptstate gupnp libplist jimtcl libmodman libimobiledevice man-pages-overrides khmeros-fonts-common gupnp-dlna gupnp-av lua-socket usbmuxd gssdp libusbmuxd
 - fix duplicate set_ids (17598, 17599) in vendors.d/mariadb_pes.json

- The package .spec:
 - add support of multiple GPG keys
 - bump release number

* Mon Feb 26 2024 Eduard Abdullin <eabdullin@almalinux.org> - 0.2-9.20230823
- Add support for migration from EL8 to EL9 for all distros with enabled epel repositories

* Thu Feb 22 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-8.20230823
- Downgrade pes-event files into 57515f42a5831e8ebe9dd3c95a7b58f8c76824ab (as of 20230823)
- Remove ustr package during EL8 to EL9 migration for the all distros

* Mon Feb 05 2024 Eduard Abdullin <eabdullin@almalinux.org> - 0.2-7.20240123
- Add generate_epel_files script to create epel files for EL7
- Add data to support migration from EL7 to EL8 with
 enabled epel repositories for AlmaLinux-8
- Add pes_events_build_date to spec file to track the pes-events update date

* Tue Jan 16 2024 Eduard Abdullin <eabdullin@almalinux.org> - 0.2-6
- Add gpg keys

* Tue Jan 16 2024 Eduard Abdullin <eabdullin@almalinux.org> - 0.2-5
- Update pes-event file for Rocky, EuroLinux, CentOS Stream, AlmaLinux

* Tue Jan 16 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.2-3.2
- Use YUM archive repo of PostgreSQL 11 for RHEL / Rocky 8 (x86_64)

* Mon Dec 11 2023 Eduard Abdullin <eabdullin@almalinux.org> - 0.2-3.1
- Fix EL8 to EL9 migration

* Mon Mar 27 2023 Andrew Lukoshko <alukoshko@almalinux.org> - 0.2-3
- Add 8 to 9 migration support for Rocky Linux, EuroLinux, CentOS Stream

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
