#!/bin/bash

if [ $# -eq 0 ]; then
    echo "No arguments provided"
    exit 1
fi

dist_name=$1
declare -A os_repos
os_repos["almalinux"]="almalinux8-appstream almalinux8-powertools"
os_repos["centos"]="centos8-appstream centos8-powertools"
os_repos["eurolinux"]="certify-appstream certify-powertools"
os_repos["oraclelinux"]="ol8_appstream ol8_codeready_builder"
os_repos["rocky"]="rocky8-appstream rocky8-powertools"

declare -A os_name
os_name["almalinux"]="AlmaLinux"
os_name["centos"]="CentOS"
os_name["eurolinux"]="EuroLinux"
os_name["oraclelinux"]="OL"
os_name["rocky"]="Rocky"

if [ -n "${os_repos[$dist_name]}" ]; then
    IFS=' ' read -ra REPO <<< "${os_repos[$dist_name]}"
    sed -i "s/{appstream}/${REPO[0]}/g" vendors.d/epel_map.json_template
    sed -i "s/{powertools}/${REPO[1]}/g" vendors.d/epel_map.json_template
    sed -i "s/{os_name}/${os_name[$dist_name]}/g" vendors.d/epel_pes.json_template

    mv vendors.d/epel_pes.json_template vendors.d/epel_pes.json
    mv vendors.d/epel_map.json_template vendors.d/epel_map.json
else
    echo "Unknown OS name"
    exit 1
fi
