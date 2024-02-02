#!/bin/bash

find . -name "*pes-events*.json" -exec python3 tests/validate_json.py tests/pes-events-schema.json {}\;
find . -name "*pes-events*.json"


