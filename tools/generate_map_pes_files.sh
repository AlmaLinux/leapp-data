#!/bin/bash

if [ $# -eq 0 ]; then
    echo "No arguments provided"
    exit 1
fi

dist_name=$1
major_ver=$2

declare -A os_repos
os_repos["almalinux7"]="almalinux8-appstream almalinux8-powertools almalinux8-baseos"
os_repos["centos7"]="centos8-appstream centos8-powertools centos8-baseos"

os_repos["almalinux8"]="almalinux9-appstream almalinux9-crb almalinux9-baseos"
os_repos["centos8"]="centos9-appstream centos9-crb centos9-baseos"

os_repos["almalinux9"]="almalinux10-appstream almalinux10-crb almalinux10-baseos"
# To generate data for leapp-data-almalinux-x86_64_v2 package on AlmaLinux 9
os_repos["almalinux-x86_64_v29"]="almalinux10-appstream almalinux10-crb almalinux10-baseos"
# To generate data for leapp-data-almalinux-kitten package on AlmaLinux 9
os_repos["almalinux-kitten9"]="almalinux10-appstream almalinux10-crb almalinux10-baseos"
os_repos["centos9"]="centos10-appstream centos10-crb centos10-baseos"

declare -A os_name
os_name["almalinux"]="AlmaLinux"
os_name["almalinux-x86_64_v2"]="AlmaLinux"
os_name["almalinux-kitten"]="AlmaLinux"
os_name["centos"]="CentOS"

# The 'distro' field in repomap files
distro=$dist_name
[[ $distro == almalinux-kitten* ]] && distro=almalinux
[[ $distro == almalinux-x86_64_v2* ]] && distro=almalinux

case $major_ver in
    7)
        target_version=8 ;;
    8)
        target_version=9 ;;
    9)
        target_version=10 ;;
    *)
        echo "Unsupported major version";
        exit 1;
        ;;
esac

epel_pes_file=vendors.d/epel_pes.json_template
epel_map_file="vendors.d/epel_map.json_template.el${target_version}"
microsoft_pes_file="vendors.d/microsoft_pes.json_template.el${target_version}"
docker_ce_map_file="vendors.d/docker-ce_map.json_template.el${target_version}"
imunify_map_file="vendors.d/imunify_map.json_template.el${target_version}"
imunify360_alt_php_map_file="vendors.d/imunify360-alt-php_map.json_template.el${target_version}"
kernelcare_map_file="vendors.d/kernelcare_map.json_template.el${target_version}"
mariadb_map_file="vendors.d/mariadb_map.json_template.el${target_version}"
microsoft_map_file="vendors.d/microsoft_map.json_template.el${target_version}"
nginx_mainline_map_file="vendors.d/nginx-mainline_map.json_template.el${target_version}"
nginx_stable_map_file="vendors.d/nginx-stable_map.json_template.el${target_version}"
postgresql_map_file="vendors.d/postgresql_map.json_template.el${target_version}"
tuxcare_map_file="vendors.d/tuxcare_map.json_template.el${target_version}"

if [ -n "${os_repos[$dist_name$major_ver]}" ]; then
    IFS=' ' read -ra REPO <<< "${os_repos[$dist_name$major_ver]}"
    for file in ${epel_map_file} \
        ${epel_pes_file} \
        ${microsoft_pes_file} \
        ${postgresql_map_file} \
        ${nginx_stable_map_file} \
        ${nginx_mainline_map_file} \
        ${microsoft_map_file} \
        ${mariadb_map_file} \
        ${kernelcare_map_file} \
        ${imunify360_alt_php_map_file} \
        ${imunify_map_file} \
        ${docker_ce_map_file} \
        ${tuxcare_map_file}; do
        test -e "${file}" || continue

        sed -i "s/{appstream}/${REPO[0]}/g" "${file}"
        sed -i "s/{powertools}/${REPO[1]}/g" "${file}"
        sed -i "s/{baseos}/${REPO[2]}/g" "${file}"
        sed -i "s/{os_name}/${os_name[$dist_name]}/g" "${file}"
        sed -i "s/{distro}/${distro}/g" "${file}"
    done

    mv "${epel_pes_file}" vendors.d/epel_pes.json
    mv "${epel_map_file}" vendors.d/epel_map.json
    mv "${microsoft_pes_file}" vendors.d/microsoft_pes.json || true
    mv "${microsoft_map_file}" vendors.d/microsoft_map.json || true
    mv "${docker_ce_map_file}" vendors.d/docker-ce_map.json
    mv "${imunify_map_file}" vendors.d/imunify_map.json || true
    mv "${imunify360_alt_php_map_file}" vendors.d/imunify360-alt-php_map.json || true
    mv "${kernelcare_map_file}" vendors.d/kernelcare_map.json || true
    mv "${mariadb_map_file}" vendors.d/mariadb_map.json || true
    mv "${nginx_mainline_map_file}" vendors.d/nginx_mainline_map.json || true
    mv "${nginx_stable_map_file}" vendors.d/nginx-stable_map.json || true
    mv "${postgresql_map_file}" vendors.d/postgresql_map.json
    mv "${tuxcare_map_file}" vendors.d/tuxcare_map.json || true

else
    echo "Unsupported OS"
    exit 1
fi
