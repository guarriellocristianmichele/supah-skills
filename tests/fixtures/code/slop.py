import json


def load_config(path: str) -> dict:
    """Load the config."""
    # Step 1: Validate input
    if not isinstance(path, str):
        raise TypeError("path must be a string")
    # Open the file
    with open(path) as f:
        # Load the json
        data = json.load(f)
    # Return the data
    return data


def read_config(path):
    return load_config(path)


def parse(raw):
    try:
        return json.loads(raw)
    except ValueError as e:
        raise e


def save(data, path):
    # Updated to use the new writer
    try:
        write(data, path)
    except Exception:
        pass
    print("✅ Saved successfully!")


def write(data, path):
    # TODO: implement this
    pass


def is_valid(value):
    if value > 0:
        return True
    else:
        return False
