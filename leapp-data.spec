%global pes_events_build_date 20251222

%define repositorydir %{_datadir}/leapp-repository/repositories

%define dist_list almalinux almalinux-kitten centos
%define conflict_dists() %(for i in almalinux almalinux-kitten centos; do if [ "${i}" != "%{dist_name}" ]; then echo -n "leapp-data-${i} "; fi; done)

%if 0%{?rhel} == 7
%define supported_vendors epel imunify kernelcare mariadb nginx-stable nginx-mainline postgresql docker-ce imunify360-alt-php tuxcare elevate
%define target_version 8
%define dist_gpg_path distro/%{dist_name}/rpm-gpg/%{target_version}
%if %{dist_name} == "almalinux"
%define gpg_key RPM-GPG-KEY-AlmaLinux-8
%endif
%if %{dist_name} == "centos"
%define gpg_key RPM-GPG-KEY-CentOS-Official
%endif
%endif
%if 0%{?rhel} == 8
%define supported_vendors epel kernelcare mariadb nginx-stable nginx-mainline postgresql docker-ce tuxcare elevate
%define target_version 9
%define dist_gpg_path distro/%{dist_name}/rpm-gpg/%{target_version}
%if "%{dist_name}" == "almalinux"
%define gpg_key RPM-GPG-KEY-AlmaLinux-9
%endif
%if "%{dist_name}" == "centos"
%define gpg_key RPM-GPG-KEY-CentOS-Official RPM-GPG-KEY-CentOS-SIG-Extras
%endif
%endif
%if 0%{?rhel} == 9
%define supported_vendors epel imunify kernelcare mariadb nginx-stable nginx-mainline docker-ce postgresql imunify360-alt-php tuxcare elevate
%define target_version 10
%define dist_gpg_path distro/%{dist_name}/rpm-gpg/%{target_version}
%if "%{dist_name}" == "almalinux"
%define gpg_key RPM-GPG-KEY-AlmaLinux-10
%endif
%if "%{dist_name}" == "almalinux-kitten"
%define gpg_key RPM-GPG-KEY-AlmaLinux-10
%define dist_gpg_path distro/almalinux/rpm-gpg/%{target_version}
%endif
%if "%{dist_name}" == "centos"
%define gpg_key RPM-GPG-KEY-centosofficial-SHA256 RPM-GPG-KEY-CentOS-SIG-Extras-SHA512
%endif
%endif

%bcond_without check

Name:		leapp-data-%{dist_name}
Version:	0.11
Release:	8%{?dist}.%{pes_events_build_date}
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
%if 0%{?rhel} >= 8
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
if [[ %{dist_name} != *"almalinux"* ]]; then
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
find %{buildroot}%{_sysconfdir}/leapp/files/vendors.d/ -name \*.el\* -a ! -name \*.el%{target_version} -delete


# Main part
cp -rf files/%{dist_name}/* %{buildroot}%{_sysconfdir}/leapp/files/

rm -f %{buildroot}%{_sysconfdir}/leapp/files/config.json

%if 0%{?rhel} == 7
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el8 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el8 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el9
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el10
%endif
%if 0%{?rhel} == 8
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el9 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el9 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el8
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el10
%endif
%if 0%{?rhel} == 9
mv -f %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo.el10 \
      %{buildroot}%{_sysconfdir}/leapp/files/leapp_upgrade_repositories.repo
mv -f %{buildroot}%{_sysconfdir}/leapp/files/repomap.json.el10 \
      %{buildroot}%{_sysconfdir}/leapp/files/repomap.json
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el9
rm -f %{buildroot}%{_sysconfdir}/leapp/files/*.el8
%endif

for key in %{gpg_key}; do
      for rpm_gpg_path in rpm-gpg/%{target_version} %{dist_gpg_path}; do
            mkdir -p %{buildroot}%{repositorydir}/system_upgrade/common/files/${rpm_gpg_path}
            cp -av files/rpm-gpg/${key} %{buildroot}%{repositorydir}/system_upgrade/common/files/${rpm_gpg_path}/
      done
      rm -f files/rpm-gpg/${key}
done

%check
%if %{with check}
JSON_FILES=$(find %{buildroot}%{_sysconfdir}/leapp/ -path "./tests" -prune -o -name "*pes*.json*" -print0 | xargs -0 echo)

python3 tests/validate_json.py tests/pes-events-schema.json $JSON_FILES
python3 tests/validate_ids.py $JSON_FILES
python3 tests/check_debranding.py %{buildroot}%{_sysconfdir}/leapp/files/pes-events.json
%endif


%files
%doc LICENSE NOTICE README.md
%{repositorydir}/system_upgrade/common/files/rpm-gpg/%{target_version}/*
%{repositorydir}/system_upgrade/common/files/%{dist_gpg_path}/*
%{_sysconfdir}/leapp/files/*


%changelog
* Mon May 04 2026 Yuriy Kohut <ykohut@almalinux.org> - 0.11-8.20251222
- Vendor EPEL: refresh epel_pes.json_template from current EPEL repodata (8to9)
 - emit REPLACED/SPLIT/MERGED from Obsoletes-driven candidates
 - skip MOVED and REMOVED actions by default

* Wed Apr 08 2026 Yuriy Kohut <ykohut@almalinux.org> - 0.11-7.20251222
- Vendor KernelCare: add 44c25eb080935b88 SIG key
- Vendor Nginx: add 2fd21310b49f6b46 SIG key
- tools/generate_map_pes_files.sh: add vendors.d/tuxcare_map.json_template.el* to the list of files to process

* Wed Mar 11 2026 Yuriy Kohut <ykohut@almalinux.org> - 0.11-6.20251222
- Vendor PostgreSQL:
 - add "PostgreSQL 18 for EL" repositories, 8 to 9 and 9 to 10 upgrade paths
 - include ppc64le architecture where it is available
 - switch "PostgreSQL 13 for EL" repositories into yum-archive.postgresql.org

* Wed Feb 11 2026 Yuriy Kohut <ykohut@almalinux.org> - 0.11-5.20251222
- Vendor MariaDB:
 - change domain into mirror.mariadb.org and set path in baseurl for mariadb-main repository

* Mon Jan 19 2026 Yuriy Kohut <ykohut@almalinux.org> - 0.11-4.20251222
- Data stream version 4.2
- Update data to the upstream most recent state:
 - PES data:
  - pes-events.json: upstream state 7fa270f33a73abe77af863598914b3e6c0c3219c
  - epel_pes.json_template:
   - remove duplicated id and set_id
  - config.json:
   - for centos add rhel8-SAP-NetWeaver, rhel8-SAP-Solutions, rhel9-SAP-NetWeaver, rhel9-SAP-Solutions, rhel10-SAP-Solutions to the "repository_replacing"
   - for almalinux, almalinux-kitten and centos add rhel10-NFV to the "repository_replacing"

* Mon Jan 19 2026 Yuriy Kohut <ykohut@almalinux.org> - 0.11-3.20251112
- Vendor PostgreSQL:
 - remove Supplementary ucommon RPMs (sysupdates) repositories
 - switch "PostgreSQL 12 for RHEL / CentOS" repositories into yum-archive.postgresql.org

* Thu Nov 27 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.11-2.20251112
- Data stream version 4.1
- Update data to the upstream most recent state:
 - PES data:
  - pes-events.json: upstream state 60c4987cf45c8c795c2e2607e376c35831aebafd
  - epel_pes.json_template:
   - remove duplicated id and set_id
  - config.json:
   - for almalinux, almalinux-kitten and centos add rhel7-jbeap-7.4, rhel8-jbeap-8.0, rhel8-jbeap-7.4, rhel8-jbeap-8.1, rhel9-jbeap-8.0, rhel9-jbeap-7.4, rhel9-jbeap-8.1, rhel-drivers to the removable repositories list
   - for almalinux, almalinux-kitten and centos add rhel-drivers to the removable packages list

* Wed Nov 26 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-8.20250729
- Vendor PostgreSQL: correct extras repository base url

* Tue Oct 21 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.11-1.20250813
- Update data to the upstream most recent state:
 - Device driver deprecation data:
  - leapp-repository sha f73be94c6d195af02bf7595e9604cac171d096e1
 - PES data:
  - pes-events.json: upstream state f73be94c6d195af02bf7595e9604cac171d096e1
  - epel_pes.json_template:
   - remove duplicated id and set_id

* Fri Oct 17 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-7.20250729
- Add new Vendor, elevate - ELevate enables upgrades between major versions of RHEL derivatives
- Add new Vendors for 9 to 10 upgrade:
  - imunify Vendor
  - imunify360-alt-php Vendor
- Vendor imunify360-alt-php update rpm GPG key
- Vendors imunify and imunify360-alt-php: update packages SIGs

* Tue Oct 14 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-6.20250729
- Add new Vendors for 9 to 10 upgrade:
  - Nginx Vendor
  - MariaDB Vendor (without MaxScale and Tools repositories)
  - Microsoft Vendor (still disabled for all upgrades)
  - KernelCare Vendor (use el-sig202505 repository)

* Thu Sep 11 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-5.20250729
- Vendor imunify: update rpm GPG key

* Fri Aug 08 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-4.20250729
- Vendor mariadb: switch into 12.rolloing repository

* Thu Aug 07 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-3.20250729
- Vendor kernelcare: use local GPG key instead of remote one
- Update data to the upstream most recent state:
 - PES data:
  - pes-events.json: upstream state 300e1579c28d630a9c0be2599083a79d441cc6b2
  - epel_pes.json_template:
   - remove duplicated id and set_id
  - config.joson (almalinux, almalinux-kitten): add redhat-cloud-client-configuration-cdn to the removable packages list, with scenarios: 9to9

* Mon Jul 21 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-2.20250711
- Update data to the upstream most recent state:
 - Device driver deprecation data:
  - leapp-repository sha 93cae9c88e964d6485ad8314ae65deb0ab676862
 - PES data:
  - pes-events.json: upstream state 93cae9c88e964d6485ad8314ae65deb0ab676862
  - epel_pes.json_template:
   - remove duplicated id and set_id

* Wed Jul 16 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.10-1.20250624
- Update all data into stream 4.0
- Update all repomap files into new format version 1.3.0. Add 'distro' field
- Rename Vendors' repositories mapping json files into templates and process them with generate_map_pes_files.sh
- Update data to the upstream most recent state:
 - PES data:
  - pes-events.json: upstream state 2544f574969626bfe99cfd8aadd8eef36ecb2841
- Bump the package version

* Fri Jul 11 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.9-4.20250505
- New vendor, tuxcare
 - add alt-common repository - alt common Extended Lifecycle Support by TuxCare

* Wed May 28 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.9-3.20250505
- Add PostgreSQL Vendor for 9 to 10 upgrade

* Wed May 28 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.9-2.20250505
- ELevate to AlmaLinux 10.0 stable

* Mon May 19 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.9-1.20250505
- Update data to the upstream most recent state:
 - Device driver deprecation data:
  - leapp-repository sha 9c621a91199c093f603ef30ba3daf59010c20e47
 - PES data:
  - pes-events.json: upstream state ffd6d8e456484630f99d98d5bff955914af02aa5
  - epel_pes.json_template:
   - remove duplicated id and set_id
- Install rpm public GPG key(s) into distro specific path
- Bump the package version

* Fri Mar 28 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.8-3.20250228
- Exclude microsoft vendor from the package

* Thu Mar 27 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.8-2.20250228
- Update pes-events.json and config.json (except almalinux-kitten, centos):
 - solve valgrind-docs, valgrind-scripts with valgrind package conflicts during 8to9 upgrade
- Bump the package release

* Thu Mar 06 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.8-1.20250228
- AlmaLinux Kitten 10 support

* Fri Feb 28 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.7-1.20250228
- Update data to the upstream most recent state:
 - Device driver deprecation data:
  - leapp-repository sha 518722058ca53e94c8efa8958ca8fd7cac40dca7

 - PES data:
  - pes-events.json: upstream state 518722058ca53e94c8efa8958ca8fd7cac40dca7
  - config.json (all distros):
   - add libreport-rhel-anaconda-bugzilla (except centos) to the removable packages list, with scenarios: 9to9, 9to10
   - add redhat-flatpak-repo, redhat-flatpak-preinstall-firefox, redhat-flatpak-preinstall-thunderbird to the removable packages list, with scenarios: 9to10
  - epel_pes.json_template:
   - remove duplicated id and set_id

* Wed Jan 15 2025 Yuriy Kohut <ykohut@almalinux.org> - 0.6-2.20241127
- ELevate to CentOS Stream release 10

* Wed Dec 18 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.6-1.20241127
- ELevate to AlmaLinux 10.0 Beta with EPEL and docker-ce vendors supported

* Tue Dec 10 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.5-2.20241127
- Drop EuroLinux support

* Thu Nov 28 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.5-1.20241127
- Update data to the upstream most recent state:
 - Device driver deprecation data:
  - leapp-repository sha 2dc7efa41ccf7206e0e33d687d7931846f3e4390
  - extended hardware support list from 9.5's RN

 - PES data:
  - pes-events.json: upstream state 2dc7efa41ccf7206e0e33d687d7931846f3e4390
  - config.json:
   - add repository replacing for rhel10-HighAvailability and rhel10-SAP-Solutions for all distros (except oraclelinux)
   - add rhel9-Supplementary to the removable repositories list
   - add rhel10-HighAvailability and rhel10-SAP-Solutions to the oraclelinux's removable repositories list
   - add redhat-cloud-client-configuration to the removable packages list, with scenarios: 7to7, 8to8, 8to9
  - epel_pes.json_template:
   - remove duplicated ids and set_ids

- Bump the package pes_events_build_date, version and release: 0.5-1.20241127

* Fri Nov 15 2024 Yuriy Kohut <ykohut@almalinux.org> - 0.4-12.20240827
- Move operating systems' GPG keys from %{_sysconfdir}/leapp/repos.d to %{repositorydir}

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
