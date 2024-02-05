import json
import argparse
from jsonschema import validate
from jsonschema.exceptions import ValidationError


def is_valid_json(json_data, schema):
    try:
        validate(instance=json_data, schema=schema)
    except ValidationError as err:
        return False, err
    return True, None


def main():
    parser = argparse.ArgumentParser(description="JSON Schema Validator")
    parser.add_argument("schema_path", help="Path to the JSON schema file")
    parser.add_argument("json_path", nargs='+', help="Path to the JSON file to validate")

    args = parser.parse_args()

    with open(args.schema_path, 'r') as schema_file:
        schema = json.load(schema_file)

    failed = False

    for file in args.json_path:
        print(f"Validating {file} against {args.schema_path}")
        with open(file, 'r') as json_file:
            try:
                json_data = json.load(json_file)
                valid, error = is_valid_json(json_data, schema)
                if valid:
                    print("JSON is valid according to the schema.")
                else:
                    print(f"JSON is invalid. Error: {error}")
                    failed = True
            except json.JSONDecodeError as err:
                print(f"Invalid JSON: {err}")
                failed = True
    if failed:
        exit(1)


if __name__ == "__main__":
    main()
