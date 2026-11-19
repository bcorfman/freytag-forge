"""Confidence intervals and calibrated judge-rate gates."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Return the Wilson score interval for a binomial rate."""

    if successes < 0 or successes > n:
        raise ValueError("successes must be between 0 and n")
    if n == 0:
        return 0.0, 1.0

    p = successes / n
    z_squared = z * z
    denominator = 1 + z_squared / n
    center = (p + z_squared / (2 * n)) / denominator
    margin = z / denominator * sqrt(p * (1 - p) / n + z_squared / (4 * n * n))
    return max(0.0, center - margin), min(1.0, center + margin)


@dataclass(frozen=True)
class ErrorRates:
    """Measured judge sensitivity and specificity counts."""

    sensitivity_hits: int
    sensitivity_n: int
    specificity_hits: int
    specificity_n: int


def corrected_lower_bound(
    successes: int,
    n: int,
    rates: ErrorRates,
    z: float = 1.96,
) -> float:
    """Return a conservative lower bound corrected for measured judge error."""

    observed_lower, _ = wilson_interval(successes, n, z)
    _, sensitivity_upper = wilson_interval(rates.sensitivity_hits, rates.sensitivity_n, z)
    specificity_lower, _ = wilson_interval(rates.specificity_hits, rates.specificity_n, z)
    denominator = sensitivity_upper + specificity_lower - 1
    if denominator <= 0:
        return 0.0

    corrected = (observed_lower + specificity_lower - 1) / denominator
    return min(1.0, max(0.0, corrected))


def gate_passes(
    successes: int,
    n: int,
    target: float,
    rates: ErrorRates,
    z: float = 1.96,
) -> bool:
    """Return whether the corrected lower bound reaches the target rate."""

    return corrected_lower_bound(successes, n, rates, z) >= target
