def compute_irr(
    cashflows: list[float],
    *,
    low: float = -0.99,
    high: float = 10.0,
    tol: float = 1e-6,
    max_iter: int = 200,
) -> float | None:
    """Bisection solver for the periodic rate that zeroes the NPV of `cashflows`.

    Returns None when there is no sign change over [low, high] — meaning the
    series has no meaningful IRR in a plausible range (e.g. it never pays
    back), which is itself a valid, reportable outcome rather than an error.
    """

    def npv(rate: float) -> float:
        return sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))

    f_low, f_high = npv(low), npv(high)
    if f_low == 0:
        return low
    if f_high == 0:
        return high
    if f_low * f_high > 0:
        return None

    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv(mid)
        if abs(f_mid) < tol:
            return mid
        if f_low * f_mid < 0:
            high, f_high = mid, f_mid
        else:
            low, f_low = mid, f_mid

    return (low + high) / 2
