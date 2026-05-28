from __future__ import annotations

import numpy as np


def estimate_seconds(n_particles: np.ndarray, lmax: int, a6: float, p6: float, ratio_5_to_6: float) -> np.ndarray:
    n = np.asarray(n_particles, dtype=float)
    t6 = a6 * np.power(n, p6)
    if int(lmax) == 6:
        return t6
    if int(lmax) == 5:
        return t6 * ratio_5_to_6
    # Conservative fallback: scale roughly as number of multipole coefficients squared.
    m6 = (6 + 1) ** 2
    ml = (int(lmax) + 1) ** 2
    return t6 * (ml / m6) ** 2


def format_duration(seconds: float) -> str:
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} min"
    hours = minutes / 60
    if hours < 48:
        return f"{hours:.2f} h"
    return f"{hours / 24:.2f} days"
