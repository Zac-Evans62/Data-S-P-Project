"""Generate the experiment's single 32-byte key. Run ONCE, then commit it.

    python scripts/generate_key.py

Refuses to overwrite an existing key. This is a demonstration key for a
class project; it is committed so graders can reproduce results.
"""
import _bootstrap  # noqa: F401

from wmark.config import generate_key, key_fingerprint, key_path, load_settings

if __name__ == "__main__":
    path = key_path(load_settings())
    key = generate_key(path)
    print(f"Wrote new key to {path}")
    print(f"Key fingerprint (safe to cite in the report): {key_fingerprint(key)}")
