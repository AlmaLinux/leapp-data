import json
import os
from dataclasses import dataclass

@dataclass
class JSONFile:
    path: str
    data: dict


def load_json(file_path: str):
    """Load JSON data from a file."""
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    # The JSON data is a dictionary with a key 'packageinfo'
    # PES events data is stored there
    return data

def save_json(jsonfile: JSONFile):
    """Save JSON data to a file."""
    with open(jsonfile.path, "w", encoding="utf-8") as file:
        json.dump(jsonfile.data, file, indent=4)


class PesIdRebuilder():
    def __init__(self):
        self.json_files = []

        self.event_id = 0
        self.set_id = 0

    def load_json_files(self, directory_list: list):
        # The PES front file should be the first one in the list
        pes_front = None

        for directory_path in directory_list:
            for filename in os.listdir(directory_path):
                if "pes" in filename:
                    file_path = os.path.join(directory_path, filename)
                    data = load_json(file_path)
                    new_json_file = JSONFile(file_path, data)
                    if "pes-events.json" in file_path:
                        pes_front = new_json_file
                    else:
                        self.json_files.append(new_json_file)

        self.json_files.insert(0, pes_front)

    def save_json_files(self):
        for jsonfile in self.json_files:
            save_json(jsonfile)

    def rebuild_ids(self):
        # Go over the "id" field and reassign the values, starting from 1
        for jsonfile in self.json_files:
            self.rebuild_ids_in_file(jsonfile.data)

    def rebuild_ids_in_file(self, file_data):
        for _, item in enumerate(file_data["packageinfo"]):
            item["id"] = self.event_id + 1
            self.event_id += 1

            if "in_packageset" in item:
                in_packageset = item["in_packageset"]
                if "package" in in_packageset and in_packageset["package"]:
                    in_packageset["set_id"] = self.set_id
                    self.set_id += 1
                else:
                    in_packageset["set_id"] = 0
            if "out_packageset" in item:
                out_packageset = item["out_packageset"]
                if "package" in out_packageset and out_packageset["package"]:
                    out_packageset["set_id"] = self.set_id
                    self.set_id += 1
                else:
                    out_packageset["set_id"] = 0

def main():
    rebuilder = PesIdRebuilder()

    os_directory_path = os.path.join(os.path.dirname(__file__), "files/cloudlinux")
    os_vendors_directory_path = os.path.join(os.path.dirname(__file__), "files/cloudlinux/vendors.d")
    common_vendors_directory_path = os.path.join(os.path.dirname(__file__), "vendors.d")
    directory_list = [os_directory_path, os_vendors_directory_path, common_vendors_directory_path]

    rebuilder.load_json_files(directory_list)
    rebuilder.rebuild_ids()
    rebuilder.save_json_files()


if __name__ == "__main__":
    main()
