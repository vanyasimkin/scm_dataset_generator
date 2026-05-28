from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def load_pickle_configs(path: str | Path) -> list[np.ndarray]:
    path = Path(path)
    with path.open("rb") as f:
        obj = pickle.load(f)
    return extract_configs(obj)


def extract_configs(obj: Any) -> list[np.ndarray]:
    """Convert common pickle structures to list[np.ndarray]."""
    if isinstance(obj, np.ndarray):
        if obj.ndim == 2:
            return [obj.astype(float, copy=False)]
        if obj.ndim == 3:
            return [obj[i].astype(float, copy=False) for i in range(obj.shape[0])]
        raise ValueError(f"Unexpected ndarray shape: {obj.shape}")

    if isinstance(obj, (list, tuple)):
        out = []
        for item in obj:
            if isinstance(item, dict):
                out.append(_extract_from_dict(item))
            else:
                out.append(np.asarray(item, dtype=float))
        return out

    if isinstance(obj, dict):
        for key in ["coordinates", "coords", "positions", "pos", "configs", "samples", "data"]:
            if key in obj:
                return extract_configs(obj[key])
        keys = list(obj.keys())
        try:
            keys = sorted(keys)
        except Exception:
            pass
        return [np.asarray(_extract_from_dict(obj[k]) if isinstance(obj[k], dict) else obj[k], dtype=float) for k in keys]

    raise ValueError(f"Unsupported pickle object type: {type(obj)}")


def _extract_from_dict(d: dict) -> np.ndarray:
    for key in ["coordinates", "coords", "positions", "pos", "r", "xy", "xyz"]:
        if key in d:
            return np.asarray(d[key], dtype=float)
    raise ValueError(f"Could not find coordinates in dict keys={list(d.keys())}")


def atomic_append_jsonl(path: str | Path, record: dict, flush: bool = True) -> None:
    """Append one JSON record. Flush+fsync makes it robust to power loss."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        if flush:
            f.flush()
            os.fsync(f.fileno())


def read_done_config_ids(jsonl_path: str | Path) -> set[int]:
    path = Path(jsonl_path)
    done: set[int] = set()
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(f"WARNING: cannot parse line {line_no} in {path}; ignoring it")
                continue
            if rec.get("status") == "ok" and "config_id" in rec:
                done.add(int(rec["config_id"]))
    return done


def write_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)
