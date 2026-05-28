from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import time
import traceback
from pathlib import Path

import numpy as np
import yaml
from tqdm import tqdm

from src.scm_dataset_generator.io_utils import (
    atomic_append_jsonl,
    load_pickle_configs,
    read_done_config_ids,
    write_json,
)
from src.scm_dataset_generator.scm_adapter import (
    compute_central_energy_for_config,
    config_to_params,
    import_scm_core,
)
from src.scm_dataset_generator.time_model import estimate_seconds, format_duration


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SCM central-particle energy dataset.")
    p.add_argument("--config", required=True, help="Path to YAML config")
    p.add_argument("--input-pkl", default=None, help="Override input_pkl from config")
    p.add_argument("--output-dir", default=None, help="Override output_dir from config")
    p.add_argument("--lmax", type=int, default=None, help="Override scm.lmax from config")
    p.add_argument("--max-configs", type=int, default=None, help="Smoke-test limit")
    p.add_argument("--no-resume", action="store_true", help="Do not skip completed configs")
    return p.parse_args()


def load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def append_csv_summary(csv_path: Path, record: dict) -> None:
    fields = [
        "config_id", "status", "n_particles", "lmax", "n_orient", "n_quad",
        "elapsed_s", "min_center_neighbor_r_over_d",
        "U_total_avg_J", "U_center_avg_J", "U_single_avg_J", "Phi_center_avg_J",
        "Phi_center_std_J", "error",
    ]
    exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(record)
        f.flush()
        os.fsync(f.fileno())


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    cfg = load_config(args.config)

    if args.input_pkl is not None:
        cfg["input_pkl"] = args.input_pkl
    if args.output_dir is not None:
        cfg["output_dir"] = args.output_dir
    if args.lmax is not None:
        cfg["scm"]["lmax"] = int(args.lmax)
    if args.max_configs is not None:
        cfg["run"]["max_configs"] = int(args.max_configs)
    if args.no_resume:
        cfg["run"]["resume"] = False

    input_pkl = Path(cfg["input_pkl"])
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    results_jsonl = output_dir / "results.jsonl"
    summary_csv = output_dir / "summary.csv"
    run_meta_json = output_dir / "run_meta.json"

    scm_core = import_scm_core(project_root)
    params = config_to_params(scm_core, cfg["scm"])
    lmax = int(cfg["scm"]["lmax"])
    dim = int(cfg["coordinates"]["dim"])
    units = str(cfg["coordinates"]["units"])

    print("Loading configs:", input_pkl)
    configs = load_pickle_configs(input_pkl)
    if cfg["run"].get("max_configs") is not None:
        configs = configs[: int(cfg["run"]["max_configs"])]

    n_particles = np.array([len(c) for c in configs], dtype=int)
    tm = cfg["time_model"]
    t_est = estimate_seconds(
        n_particles,
        lmax=lmax,
        a6=float(tm["a6"]),
        p6=float(tm["p6"]),
        ratio_5_to_6=float(tm["ratio_5_to_6"]),
    )

    done = read_done_config_ids(results_jsonl) if bool(cfg["run"].get("resume", True)) else set()
    remaining_ids = [i for i in range(len(configs)) if i not in done]
    remaining_est = float(np.sum(t_est[remaining_ids])) if remaining_ids else 0.0

    print("=" * 80)
    print("SCM dataset generation")
    print("input_pkl:       ", input_pkl)
    print("output_dir:      ", output_dir)
    print("lmax:            ", lmax)
    print("n_orient:        ", params.n_orient)
    print("n_quad:          ", params.n_quad)
    print("configs total:   ", len(configs))
    print("configs done:    ", len(done))
    print("configs remain:  ", len(remaining_ids))
    print("N particles:     ", f"min={n_particles.min()}, median={np.median(n_particles):.1f}, max={n_particles.max()}")
    print("estimated remain:", format_duration(remaining_est))
    print("estimated total: ", format_duration(float(np.sum(t_est))))
    print("results_jsonl:   ", results_jsonl)
    print("summary_csv:     ", summary_csv)
    print("=" * 80)

    write_json(run_meta_json, {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "host": platform.node(),
        "platform": platform.platform(),
        "input_pkl": str(input_pkl),
        "output_dir": str(output_dir),
        "config": cfg,
        "n_configs": len(configs),
        "n_done_at_start": len(done),
        "n_remaining_at_start": len(remaining_ids),
        "estimated_remaining_s": remaining_est,
        "estimated_total_s": float(np.sum(t_est)),
    })

    print("Building quadrature normals...")
    normals = scm_core.fibonacci_sphere_points(int(params.n_quad))

    iterator = tqdm(remaining_ids, disable=not bool(cfg["run"].get("tqdm", True)), desc="SCM configs")
    for config_id in iterator:
        t0 = time.perf_counter()
        try:
            rec = compute_central_energy_for_config(
                config=configs[config_id],
                config_id=config_id,
                scm_core=scm_core,
                params=params,
                normals=normals,
                lmax=lmax,
                dim=dim,
                units=units,
            )
        except Exception as e:
            rec = {
                "status": "error",
                "config_id": int(config_id),
                "n_particles": int(len(configs[config_id])),
                "lmax": int(lmax),
                "error": repr(e),
                "traceback": traceback.format_exc(),
            }

        rec["elapsed_s"] = float(time.perf_counter() - t0)
        rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Append after every config: safe resume after power loss.
        atomic_append_jsonl(results_jsonl, rec, flush=True)
        append_csv_summary(summary_csv, rec)

    print("Done.")
    print("Results:", results_jsonl)
    print("Summary:", summary_csv)


if __name__ == "__main__":
    main()
