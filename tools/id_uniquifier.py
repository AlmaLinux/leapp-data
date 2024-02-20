import json
import argparse
from collections import defaultdict


def generate_new_id(existing_ids):
    new_id = max(existing_ids) + 1 if existing_ids else 1
    existing_ids.add(new_id)
    return new_id


def find_and_replace_duplicates(files):
    id_counts = defaultdict(int)
    set_id_counts = defaultdict(int)
    set_id_package_names = defaultdict(set)
    existing_ids = set()
    existing_set_ids = set()

    for file_path in files:
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            for item in data["packageinfo"]:
                id_counts[item["id"]] += 1
                existing_ids.add(item["id"])

                for set_type in ["in_packageset", "out_packageset"]:
                    if set_type in item and item[set_type]:
                        set_id = item[set_type]["set_id"]
                        set_id_counts[set_id] += 1
                        existing_set_ids.add(set_id)
                        if "package" in item[set_type]:
                            for package in item[set_type]["package"]:
                                set_id_package_names[set_id].add(package["name"])

        except json.JSONDecodeError as err:
            print(f"Error reading JSON file {file_path}: {err}")
        except KeyError as err:
            print(f"Key error in file {file_path}: {err}")

    for file_path in files:
        if "files" in file_path:
            continue
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            data_modified = False
            for item in data["packageinfo"]:
                if id_counts[item["id"]] > 1:
                    item["id"] = generate_new_id(existing_ids)
                    data_modified = True

                for set_type in ["in_packageset", "out_packageset"]:
                    if set_type in item and item[set_type]:
                        set_id = item[set_type]["set_id"]
                        if set_id_counts[set_id] > 1 and len(set_id_package_names[set_id]) > 1:
                            item[set_type]["set_id"] = generate_new_id(existing_set_ids)
                            data_modified = True

            if data_modified:
                with open(file_path, 'w') as file:
                    json.dump(data, file, indent=4)
        except json.JSONDecodeError as err:
            print(f"Error reading JSON file {file_path}: {err}")
        except KeyError as err:
            print(f"Key error in file {file_path}: {err}")


def main():
    parser = argparse.ArgumentParser(description="Find and Replace Duplicate IDs and Set_IDs in JSON Files")
    parser.add_argument('files', nargs='+', help='Paths to JSON files')
    args = parser.parse_args()

    find_and_replace_duplicates(args.files)
    print("Duplicate ids and set_ids have been replaced in files not containing 'files' in their path.")


if __name__ == "__main__":
    main()
