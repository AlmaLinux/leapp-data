import json
import argparse
from collections import defaultdict

def find_duplicates_in_files(files):
    id_counts = defaultdict(int)
    set_id_counts = defaultdict(int)
    set_id_package_names = defaultdict(set)

    for file_path in files:
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)

            for item in data["packageinfo"]:
                id_counts[item["id"]] += 1

                for set_type in ["in_packageset", "out_packageset"]:
                    if set_type in item and item[set_type]:
                        set_id = item[set_type]["set_id"]
                        set_id_counts[set_id] += 1
                        if "package" in item[set_type]:
                            for package in item[set_type]["package"]:
                                set_id_package_names[set_id].add(package["name"])

        except json.JSONDecodeError as err:
            print(f"Error reading JSON file {file_path}: {err}")
        except KeyError as err:
            print(f"Key error in file {file_path}: {err}")

    duplicate_ids = [item for item, count in id_counts.items() if count > 1]
    duplicate_set_ids = [item for item, count in set_id_counts.items() if count > 1]

    filtered_duplicate_set_ids = []
    for set_id in duplicate_set_ids:
        if len(set_id_package_names[set_id]) > 1:
            filtered_duplicate_set_ids.append(set_id)

    return duplicate_ids, filtered_duplicate_set_ids

def main():
    parser = argparse.ArgumentParser(description="Find Duplicate IDs and Set_IDs in Multiple JSON Files")
    parser.add_argument('files', nargs='+', help='Paths to JSON files')
    args = parser.parse_args()

    failed = False

    duplicate_ids, duplicate_set_ids = find_duplicates_in_files(args.files)

    if duplicate_ids:
        print(f"Found duplicate ids across files: {duplicate_ids}")
        failed = True
    else:
        print("No duplicate ids found across files.")

    if duplicate_set_ids:
        print(f"Found duplicate set_ids across files with different package names: {duplicate_set_ids}")
        failed = True
    else:
        print("No duplicate set_ids found across files, or duplicates have the same package names.")

    if failed:
        exit(1)

if __name__ == "__main__":
    main()
