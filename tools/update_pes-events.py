# https://raw.githubusercontent.com/oamg/leapp-repository/master/etc/leapp/files/pes-events.json
import json
import os
import requests



def download_pes_events():
    url = 'https://raw.githubusercontent.com/oamg/leapp-repository/master/etc/leapp/files/pes-events.json'
    response = requests.get(url)
    return response.json()


def read_config_file(dist_name):
    with open(f'../files/{dist_name}/config.json', 'r') as file:
        return json.load(file)


def update_os_names(os_names, pes_events_data):
    for package in pes_events_data['packageinfo']:
        for release_type in ['initial_release', 'release']:
            if release_type in package.keys() and package[release_type] is not None:
                for os_data in os_names:
                    if os_data['major_version'] == package[release_type]['major_version']:
                        package[release_type]['os_name'] = os_data['os_name']


def update_repositories(repository_compliance, pes_events_data):
    for package in pes_events_data['packageinfo']:
        for packageset in ['out_packageset', 'in_packageset']:
            if packageset in package.keys() and package[packageset] is not None:
                for specific_package in package[packageset]['package']:
                    for repo_name in repository_compliance:
                        if repo_name == specific_package['repository']:
                            specific_package['repository'] = repository_compliance[repo_name][packageset]


def remove_specific_repositories(remove_repositories, pes_events_data):
    actions_to_remove = []

    for package in pes_events_data['packageinfo']:
        for packageset in ['out_packageset', 'in_packageset']:
            if packageset in package.keys() and package[packageset] is not None:
                for specific_package in package[packageset]['package']:
                    for repo_name in remove_repositories:
                        if (
                            repo_name == specific_package['repository'] and 
                            package not in actions_to_remove
                        ):
                            actions_to_remove.append(package)
    for action in actions_to_remove:
        print(action)
        pes_events_data['packageinfo'].remove(action)


def update_pes_events(dist_name, pes_events_data):
    configuration = read_config_file(dist_name)
    
    update_os_names(configuration['os_names'], pes_events_data)
    update_repositories(configuration['repository_compliance'], pes_events_data)
    remove_specific_repositories(configuration['removable_repositories'], pes_events_data)


def main():
    pes_events_data = download_pes_events()
    for dist_name in ['almalinux']:
    # for dist_name in ['almalinux', 'centos', 'oraclelinux', 'eurolinux', 'rocky']:
        update_pes_events(dist_name, pes_events_data)
    
    with open('pes-events-test.json', 'w') as file:
        file.write(json.dumps(pes_events_data, indent=4))
    print('Done')


if __name__ == '__main__':
    main()
