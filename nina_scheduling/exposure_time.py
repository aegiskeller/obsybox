#!/usr/bin/env python3
"""
Exposure time utility

Provides a function to compute recommended exposure time (seconds)
from a given primary magnitude (mag1) using a small lookup table and
linear interpolation. The table (mag, exposure) is:

  (9, 5), (9.8, 7), (10.8, 8), (11.5, 30), (14, 140)

The function clips to the table range by default to avoid extreme
extrapolations.
"""
from typing import List, Tuple
try:
    import numpy as np
except Exception:
    np = None

# Lookup table (mag, exposure_seconds)
_TABLE: List[Tuple[float, float]] = [
    (9.0, 5.0),
    (9.8, 7.0),
    (10.8, 8.0),
    (11.5, 30.0),
    (14.0, 140.0),
]

def get_exposure_time(mag: float, *, method: str = 'linear', clip: bool = True, round_to: float = 1.0) -> float:
    """
    Return an exposure time (seconds) for a given primary magnitude `mag`.

    Args:
        mag: primary magnitude (mag1)
        method: currently only 'linear' supported (linear interpolation)
        clip: if True, clip to the table min/max instead of extrapolating
        round_to: round result to this many seconds (use 1.0 for integer seconds)

    Returns:
        exposure time in seconds (float)
    """
    mags = [m for m, _ in _TABLE]
    exps = [e for _, e in _TABLE]

    if method != 'linear':
        raise ValueError("Unsupported method; only 'linear' is implemented")

    # Use numpy if available for convenience
    if np is not None:
        mags_arr = np.array(mags, dtype=float)
        exps_arr = np.array(exps, dtype=float)
        if clip:
            mag_clamped = float(max(min(mag, mags_arr.max()), mags_arr.min()))
            exp = float(np.interp(mag_clamped, mags_arr, exps_arr))
        else:
            exp = float(np.interp(mag, mags_arr, exps_arr, left=None, right=None))
    else:
        # Pure-python linear interpolation
        if mag <= mags[0]:
            exp = exps[0]
        elif mag >= mags[-1]:
            exp = exps[-1]
        else:
            # find interval
            for i in range(len(mags)-1):
                m0, m1 = mags[i], mags[i+1]
                e0, e1 = exps[i], exps[i+1]
                if m0 <= mag <= m1:
                    t = (mag - m0) / (m1 - m0)
                    exp = e0 + t * (e1 - e0)
                    break

    # Round to requested precision
    if round_to and round_to > 0:
        exp = round(exp / float(round_to)) * float(round_to)

    return float(exp)


if __name__ == '__main__':
    # Quick test output for sample magnitudes
    sample_mags = [9.0, 9.8, 10.8, 11.5, 14.0, 12.0]
    for m in sample_mags:
        print(f"mag={m} -> exposure={get_exposure_time(m)} s")
