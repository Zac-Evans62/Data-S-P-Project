"""Fix the settings before evaluation """
import _bootstrap  # noqa: F401

from datetime import datetime
from fractions import Fraction

from wmark.config import key_fingerprint, load_key, load_settings, save_settings

if __name__ == "__main__":
    s = load_settings()
    if s.get("frozen"):
        raise SystemExit(f"Already frozen at {s.get('frozen_at')}.")
    if s.get("threshold") is None or s.get("watermark_target") is None:
        raise SystemExit("Set both \"threshold\" and \"watermark_target\" (as strings, e.g. \"0.60\") in config/settings.json first.")
    t, target = Fraction(str(s["threshold"])), Fraction(str(s["watermark_target"]))
    if not target > t:
        raise SystemExit(f"watermark_target ({target}) must be strictly above threshold ({t}).")
    key = load_key(s)
    s.update(frozen=True, frozen_at=datetime.now().isoformat(timespec="seconds"),
             key_fingerprint=key_fingerprint(key))
    save_settings(s)
    print(f"Frozen: threshold {s['threshold']}, target {s['watermark_target']}, "
          f"time limit {s['stopping_rule_max_minutes']} min, key {s['key_fingerprint']}.")
    print("Now: git commit config/settings.json, then `git tag settings-frozen`.")
