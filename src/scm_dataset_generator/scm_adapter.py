from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np


def import_scm_core(project_root: Path):
    vendor = project_root / "vendor"
    if str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    try:
        import scm_core  # type: ignore
    except Exception as e:
        raise ImportError(
            "Cannot import vendor/scm_core.py. Copy it from "
            "https://github.com/vanyasimkin/article_scm_triplets into vendor/scm_core.py "
            "or run: python scripts/fetch_scm_core.py"
        ) from e
    return scm_core


def config_to_params(scm_core: Any, cfg: dict):
    return scm_core.SCMParams(
        eps1_r=float(cfg["eps1_r"]),
        eps2_r=float(cfg["eps2_r"]),
        a=float(cfg["a"]),
        E0=float(cfg["E0"]),
        eps0=float(cfg["eps0"]),
        n_orient=int(cfg["n_orient"]),
        n_quad=int(cfg["n_quad"]),
    )


def centers_to_si(config: np.ndarray, *, dim: int, units: str, params: Any) -> np.ndarray:
    """
    Input config convention:
    - config[0] is central particle at origin;
    - config[:, :dim] are coordinates.

    Output is an (N, 3) SI array for SCM.
    """
    arr = np.asarray(config, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"Config must be 2D, got shape={arr.shape}")
    if arr.shape[1] < dim:
        raise ValueError(f"Config has {arr.shape[1]} columns, dim={dim}")

    coords = arr[:, :dim]
    if dim == 2:
        centers = np.zeros((arr.shape[0], 3), dtype=float)
        centers[:, :2] = coords
    elif dim == 3:
        centers = coords.copy()
    else:
        raise ValueError("dim must be 2 or 3")

    if units == "diameter":
        centers *= params.d
    elif units == "radius":
        centers *= params.a
    elif units == "meter":
        pass
    else:
        raise ValueError("coordinates.units must be one of: diameter, radius, meter")

    return centers


def compute_central_energy_for_config(
    *,
    config: np.ndarray,
    config_id: int,
    scm_core: Any,
    params: Any,
    normals: np.ndarray,
    lmax: int,
    dim: int,
    units: str,
) -> dict:
    centers = centers_to_si(config, dim=dim, units=units, params=params)

    if centers.shape[0] < 1:
        raise ValueError("Empty config")
    if not np.allclose(centers[0], 0.0, atol=1e-14):
        raise ValueError(
            f"config_id={config_id}: config[0] must be central particle at origin; got {centers[0]}"
        )

    system = scm_core.MatrixSCMSystem(
        centers=centers,
        lmax=int(lmax),
        normals=normals,
        params=params,
    )

    U_total_k = []
    U_center_k = []
    Phi_center_k = []
    U_single_k = []

    for k in range(int(params.n_orient)):
        E_vec = scm_core.rotating_field_k(k, params)
        U_total, U_parts = system.energy_parts(E_vec)
        U1 = scm_core.analytic_single_sphere_bem_like_energy(E_vec, params)

        U_total_k.append(float(U_total))
        U_center_k.append(float(U_parts[0]))
        U_single_k.append(float(U1))
        Phi_center_k.append(float(U_parts[0] - U1))

    U_total_k = np.array(U_total_k, dtype=float)
    U_center_k = np.array(U_center_k, dtype=float)
    U_single_k = np.array(U_single_k, dtype=float)
    Phi_center_k = np.array(Phi_center_k, dtype=float)

    pair_min_over_d = np.nan
    if centers.shape[0] > 1:
        r = np.linalg.norm(centers[1:] - centers[0], axis=1)
        pair_min_over_d = float(np.min(r / params.d))

    return {
        "status": "ok",
        "config_id": int(config_id),
        "n_particles": int(centers.shape[0]),
        "lmax": int(lmax),
        "n_orient": int(params.n_orient),
        "n_quad": int(params.n_quad),
        "min_center_neighbor_r_over_d": pair_min_over_d,
        "U_total_avg_J": float(np.mean(U_total_k)),
        "U_total_std_J": float(np.std(U_total_k)),
        "U_center_avg_J": float(np.mean(U_center_k)),
        "U_center_std_J": float(np.std(U_center_k)),
        "U_single_avg_J": float(np.mean(U_single_k)),
        "Phi_center_avg_J": float(np.mean(Phi_center_k)),
        "Phi_center_std_J": float(np.std(Phi_center_k)),
        "U_total_orient_J": U_total_k.tolist(),
        "U_center_orient_J": U_center_k.tolist(),
        "U_single_orient_J": U_single_k.tolist(),
        "Phi_center_orient_J": Phi_center_k.tolist(),
    }
