#!/bin/bash

if [ $# -eq 0 ]; then
    echo "No arguments provided"
    exit 1
fi

dist_name=$1
major_ver=$2
arch=$(rpm -E %_arch)

declare -A os_repos
os_repos["almalinux7"]="almalinux8-appstream almalinux8-powertools almalinux8-baseos"
os_repos["centos7"]="centos8-appstream centos8-powertools centos8-baseos"
os_repos["eurolinux7"]="certify-appstream certify-powertools certify-baseos"
os_repos["oraclelinux7"]="ol8_appstream ol8_codeready_builder ol8-baseos"
os_repos["rocky7"]="rocky8-appstream rocky8-powertools rocky8-baseos"

os_repos["almalinux8"]="almalinux9-appstream almalinux9-crb almalinux9-baseos"
os_repos["centos8"]="centos9-appstream centos9-crb centos9-baseos"
os_repos["eurolinux8"]="certify-appstream certify-crb certify-baseos"
os_repos["oraclelinux8"]="ol9_appstream ol9_codeready_builder ol9_baseos"
os_repos["rocky8"]="rocky9-appstream rocky9-crb rocky9-baseos"

declare -A os_name
os_name["almalinux"]="AlmaLinux"
os_name["centos"]="CentOS"
os_name["eurolinux"]="EuroLinux"
os_name["oraclelinux"]="OL"
os_name["rocky"]="Rocky"

case $major_ver in
    7)
        target_version=8 ;;
    8)
        target_version=9 ;;
    *)
        echo "Unsupported major version";
        exit 1;
        ;;
esac

distro_map_file="files/${dist_name}/repomap.json.el${target_version}"
if test -e "${distro_map_file}.in"; then
    sed -i "s/{arch}/${arch}/g" "${distro_map_file}.in" && \
    mv -f "${distro_map_file}.in" "${distro_map_file}"
fi

epel_pes_file=vendors.d/epel_pes.json_template
epel_map_file="vendors.d/epel_map.json_template.el${target_version}"
microsoft_pes_file="vendors.d/microsoft_pes.json_template.el${target_version}"

if [ -n "${os_repos[$dist_name$major_ver]}" ]; then
    IFS=' ' read -ra REPO <<< "${os_repos[$dist_name$major_ver]}"
    for file in ${epel_map_file} ${epel_pes_file} ${microsoft_pes_file}; do
        test -e "${file}" || continue

        sed -i "s/{appstream}/${REPO[0]}/g" "${file}"
        sed -i "s/{powertools}/${REPO[1]}/g" "${file}"
        sed -i "s/{baseos}/${REPO[2]}/g" "${file}"
        sed -i "s/{os_name}/${os_name[$dist_name]}/g" "${file}"
    done

    mv ${epel_pes_file} vendors.d/epel_pes.json
    mv ${epel_map_file} vendors.d/epel_map.json
    mv ${microsoft_pes_file} vendors.d/microsoft_pes.json
else
    echo "Unsupported OS"
    exit 1
fi
