#!/bin/bash

# AlmaLinux releases
releases=('8.10' '9.4')

# Path where to store device driver deprecation data file
# '../files/almalinux'
dist_name=almalinux
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
result_path="${parent_path}/../files/${dist_name}/"

# Data stream version, which is currenyly supported by ELevate
provided_data_streams="3.1"

# Date stamp to add to device driver deprecation data
date_stamp=$(date -u '+%Y%m%d%H%M%S')

# AlmaLinux wiki GitHub URL, release notes file, and Git SHA
release_notes_url=https://raw.githubusercontent.com/AlmaLinux/wiki
release_notes_sha=master

# Upstream leapp-repository GitHub URL, device driver deprecation data (in JSON format) file name, and Git SHA
leapp_repository_url=https://raw.githubusercontent.com/oamg/leapp-repository
device_driver_deprecation_data_json="device_driver_deprecation_data.json"
leapp_repository_sha=a757c6d0c269008ba7688c4273899dd53ca31756

printf "\nDownload %s at %s\n" ${device_driver_deprecation_data_json} ${leapp_repository_sha}
curl -s -o ${device_driver_deprecation_data_json} ${leapp_repository_url}/${leapp_repository_sha}/etc/leapp/files/${device_driver_deprecation_data_json} || exit 1

printf "\nAppend provided_data_streams with '%s'\n" ${provided_data_streams}
cat << 'EOF' > tmp.jq
if .provided_data_streams|index($provided_data_streams)|not
then .provided_data_streams |= .+ [$provided_data_streams]
else .
end
EOF
jq --arg provided_data_streams "$provided_data_streams" -f tmp.jq ${device_driver_deprecation_data_json} \
    > ${device_driver_deprecation_data_json}.tmp
[ -f ${device_driver_deprecation_data_json}.tmp ] && \
    mv -f ${device_driver_deprecation_data_json}.tmp ${device_driver_deprecation_data_json}
rm -f tmp.jq

printf "\nSet created_at to %s\n" "${date_stamp}"
jq --arg created_at "$date_stamp" '.created_at |= $created_at' ${device_driver_deprecation_data_json} \
    > ${device_driver_deprecation_data_json}.tmp
[ -f ${device_driver_deprecation_data_json}.tmp ] && \
    mv -f ${device_driver_deprecation_data_json}.tmp ${device_driver_deprecation_data_json}

for version in "${releases[@]}"; do
    printf "\nProcessing %s for AlmaLinux release %s ...\n" ${device_driver_deprecation_data_json} ${version}

    version_major=${version%.*}
    release_notes_md="${version}.md"

    echo "  Download ${release_notes_md} at ${release_notes_sha}"
    curl -s -o ${release_notes_md} ${release_notes_url}/${release_notes_sha}/docs/release-notes/${release_notes_md} || exit 1

    while read -r delimiter1 id delimiter2 name delimiter3 driver delimiter4; do
        echo "$id" | grep -E '0x.*:' >/dev/null || continue
        [ "${id}" = "" ] && continue
        # Lowercase IDs
        id="$(echo "$id" | tr '[:upper:]' '[:lower:]')"

        rm -f ${device_driver_deprecation_data_json}.tmp tmp.jq

        if echo "'$id'" | grep -E '\*' >/dev/null; then
            id="^${id}"
	    echo "  Search rexexp '${id}'"

            cat << EOF > tmp.jq
( .data[] | select( .device_id? | match("$id"; "i") ) )
EOF
        else
	    echo "  Search '${id}'"
            cat << EOF > tmp.jq
( .data[] | select( ( .device_id | ascii_downcase ) == "$id" ) )
EOF
        fi
        cat << EOF >> tmp.jq
.available_in_rhel |= .+ [$version_major]
EOF
        jq -f tmp.jq ${device_driver_deprecation_data_json} > ${device_driver_deprecation_data_json}.tmp
        [ -f ${device_driver_deprecation_data_json}.tmp ] && \
            mv -f ${device_driver_deprecation_data_json}.tmp ${device_driver_deprecation_data_json}
    done < "${release_notes_md}"

    rm -f "${release_notes_md}" tmp.jq
    unset delimiter1 id delimiter2 name delimiter3 driver delimiter4
done

printf "\nMove %s to %s\n" ${device_driver_deprecation_data_json} "${result_path}"
mkdir -p "${result_path}" && mv -f "${device_driver_deprecation_data_json}" "${result_path}/"