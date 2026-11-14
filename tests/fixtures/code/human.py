import json
import os


def load_config(path, defaults=None):
    """Read a JSON config, falling back to defaults when the file is missing.

    Keys in the file win over defaults; unknown keys are kept.
    """
    merged = dict(defaults or {})
    try:
        with open(path) as f:
            merged.update(json.load(f))
    except FileNotFoundError:
        pass  # first run: no config yet
    except ValueError as e:
        raise ValueError("%s: %s" % (path, e)) from e
    return merged


def config_path(app):
    # XDG on Linux; Windows and macOS keep it in the home folder
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, app, "config.json")


def retry(fn, attempts=3):
    for i in range(attempts):
        try:
            return fn()
        except OSError:
            if i == attempts - 1:
                raise


class Store:
    def __init__(self, path):
        self.path = path

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return list(load_config(self.path))

    def get(self, key, default=None):
        return load_config(self.path).get(key, default)
