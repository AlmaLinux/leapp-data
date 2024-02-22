import json
import requests

specific_commit = '57515f42a5831e8ebe9dd3c95a7b58f8c76824ab'


def download_pes_events(session, url):
    response = session.get(url)
    return response.json()


def read_config_file(dist_name):
    with open(f'../files/{dist_name}/config.json', 'r') as file:
        return json.load(file)


def is_package_match(package_name, release, initial_release, removable_packages):
    for i in removable_packages:
        if (
            i['name'] == package_name and 
            i['target_release'] == release and
            i['initial_release'] == initial_release
        ):
            return i
    return False


def update_os_names(os_names, pes_events_data):
    os_names_dict = {os_data['major_version']: os_data['os_name'] for os_data in os_names}

    for package in pes_events_data['packageinfo']:
        for release_type in ['initial_release', 'release']:
            if package.get(release_type) and package[release_type].get('major_version') in os_names_dict:
                package[release_type]['os_name'] = os_names_dict[package[release_type]['major_version']]


def update_data(package_replacing, repository_replacing,pes_events_data):
    repo_comp_dict = {repo_name: comp for repo_name, comp in repository_replacing.items()}
    packagesets = ['out_packageset', 'in_packageset']

    for package in pes_events_data['packageinfo']:
        for packageset in packagesets:
            if packageset in package and package[packageset]:
                for specific_package in package[packageset]['package']:
                    replacement = is_package_match(
                        specific_package['name'],
                        package['release']['major_version'] if 'release' in package and package['release'] is not None else None,
                        package['initial_release']['major_version'] if 'initial_release' in package and package['initial_release'] is not None else None,
                        package_replacing
                    )
                    if replacement:
                        if isinstance(replacement['to'], dict) and packageset in replacement['to'].keys():
                            specific_package['name'] = replacement['to'][packageset]
                        else:
                            specific_package['name'] = replacement['to']
                    if specific_package['repository'] in repo_comp_dict:
                        repository = repo_comp_dict[specific_package['repository']][packageset]
                        if (
                            (
                                'release' in package and package['release'] is not None and
                                'initial_release' in package and package['initial_release'] is not None and
                                package['release']['major_version'] == package['initial_release']['major_version']
                            ) or
                            (package['action'] == 0) or
                            (package['action'] == 2)

                        ):
                            repository = repo_comp_dict[specific_package['repository']]['out_packageset']
                        specific_package['repository'] = repository


def remove_data(remove_packages, remove_repositories, pes_events_data):
    repos_set = set(remove_repositories)
    def package_filter(package):
        for packageset in ['out_packageset', 'in_packageset']:
            if packageset in package and package[packageset] is not None:
                for specific_package in package[packageset]['package']:
                    if (
                        is_package_match(
                            specific_package['name'],
                            package['release']['major_version'] if 'release' in package and package['release'] is not None else None,
                            package['initial_release']['major_version'] if 'initial_release' in package and package['initial_release'] is not None else None,
                            remove_packages
                        ) or 
                        any(specific_package['repository'] in repos_set for specific_package in package[packageset]['package'])
                    ):
                        return False
        return True

    filtered_packages = filter(package_filter, pes_events_data['packageinfo'])
    pes_events_data['packageinfo'] = list(filtered_packages)


def add_new_packages(additional_actions, pes_events_data):
    def generate_new_id(existing_ids):
        new_id = max(existing_ids) + 1 if existing_ids else 1
        existing_ids.add(new_id)
        return new_id
    
    existing_ids = set()
    existing_set_ids = set()
    
    for package in pes_events_data['packageinfo']:
        existing_ids.add(package['id'])
        for packageset in ['out_packageset', 'in_packageset']:
            if packageset in package and package[packageset] is not None:
                existing_set_ids.add(package[packageset]['set_id'])

    for action in additional_actions:
        action['id'] = generate_new_id(existing_ids)
        for packageset in ['out_packageset', 'in_packageset']:
            if packageset in action and action[packageset] is not None:
                action[packageset]['set_id'] = generate_new_id(existing_set_ids)
        pes_events_data['packageinfo'].append(action)


def update_pes_events(dist_name, pes_events_data):
    configuration = read_config_file(dist_name)

    update_os_names(configuration['os_names'], pes_events_data)
    update_data(configuration['package_replacing'], configuration['repository_replacing'], pes_events_data)
    remove_data(configuration['removable_packages'], configuration['removable_repositories'], pes_events_data)
    add_new_packages(configuration['additional_actions'], pes_events_data)


def main():
    with requests.Session() as session:
        if specific_commit:
            pes_events_url = f'https://raw.githubusercontent.com/oamg/leapp-repository/{specific_commit}/etc/leapp/files/pes-events.json'
        else:
            pes_events_url = 'https://raw.githubusercontent.com/oamg/leapp-repository/master/etc/leapp/files/pes-events.json'

        for dist_name in ['almalinux', 'oraclelinux', 'centos', 'rocky', 'eurolinux']:
            print(f'Updating {dist_name}')
            pes_events_data = download_pes_events(session, pes_events_url)
            update_pes_events(dist_name, pes_events_data)
            with open(f'../files/{dist_name}/pes-events.json', 'w') as file:
                json.dump(pes_events_data, file, indent=4)

    print('Done')


if __name__ == '__main__':
    main()
