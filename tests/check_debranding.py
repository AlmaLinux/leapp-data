import argparse


lines_to_detect = [
    "rhel7-",
    "rhel8-",
    "rhel9-",
    "redhat-",
    "rhel10-",
    "rhel-",
]
excludes = [
    '"name": "redhat-access-plugin-ipa"',
    '"name": "redhat-rpm-config"',
    '"name": "redhat-lsb-supplemental"',
    '"name": "redhat-upgrade-tool"',
    '"name": "redhat-upgrade-dracut"',
    '"name": "redhat-upgrade-dracut-plymouth"',
    '"name": "redhat-access-gui"',
    '"name": "redhat-support-tool"',
    '"name": "redhat-support-lib-python"',
    '"name": "redhat-menus"',
    '"name": "kmod-redhat-oracleasm"',
    '"name": "redhat-display-fonts"',
    '"name": "redhat-mono-fonts"',
    '"name": "redhat-text-fonts"',
    '"name": "redhat-lsb"',
    '"name": "redhat-lsb-core"',
    '"name": "redhat-lsb-cxx"',
    '"name": "redhat-lsb-languages"',
    '"name": "redhat-lsb-printing"',
    '"name": "redhat-lsb-submod-security"',
    '"name": "redhat-lsb-trialuse"',
    '"name": "redhat-lsb-desktop"',
    '"name": "redhat-lsb-submod-multimedia"',
    '"name": "rhel-system-roles"',
    '"name": "docker-rhel-push-plugin"',
    '"name": "rhel-system-roles-sap"',
    '"name": "libreport-rhel-bugzilla"'
]


def is_in_exclude(line):
    for e in excludes:
        if e in line:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "pes_events",
        nargs='+',
        help="Path to the pes-events file to validate"
    )

    args = parser.parse_args()

    failed = False

    for file in args.pes_events:
        with open(file, 'r') as pes_events:
            for line in pes_events:
                for l in lines_to_detect:
                    if l in line and not is_in_exclude(line):
                        print(f"Found {l} in {file} at line \n{line}")
                        failed = True
                        break
            if failed:
                break


if __name__ == "__main__":
    main()
