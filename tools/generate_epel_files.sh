#!/bin/bash

if [ $# -eq 0 ]; then
    echo "No arguments provided"
    exit 1
fi

dist_name=$1
major_ver=$2

declare -A os_repos
os_repos["almalinux7"]="almalinux8-appstream almalinux8-powertools"
os_repos["centos7"]="centos8-appstream centos8-powertools"
os_repos["eurolinux7"]="certify-appstream certify-powertools"
os_repos["oraclelinux7"]="ol8_appstream ol8_codeready_builder"
os_repos["rocky7"]="rocky8-appstream rocky8-powertools"

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


if [[ $major_ver -eq 7 ]]; then
    epel_map_file="vendors.d/epel_map.json_template.el8"
elif [[ $major_ver -eq 8 ]]; then
    epel_map_file="vendors.d/epel_map.json_template.el9"
else
    echo "Unknown OS version"
    exit 1
fi

if [ -n "${os_repos[$dist_name$major_ver]}" ]; then
    IFS=' ' read -ra REPO <<< "${os_repos[$dist_name$major_ver]}"
    sed -i "s/{appstream}/${REPO[0]}/g" ${epel_map_file}
    sed -i "s/{powertools}/${REPO[1]}/g" ${epel_map_file}
    sed -i "s/{baseos}/${REPO[2]}/g" ${epel_map_file}
    sed -i "s/{os_name}/${os_name[$dist_name]}/g" vendors.d/epel_pes.json_template

    mv vendors.d/epel_pes.json_template vendors.d/epel_pes.json
    mv ${epel_map_file} vendors.d/epel_map.json
else
    echo "Unknown OS name"
    exit 1
fi
