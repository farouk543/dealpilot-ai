def monthly_payment(loan_amount: float, annual_rate_pct: float, term_years: int) -> float:
    n = term_years * 12
    r = annual_rate_pct / 100 / 12
    if r == 0:
        return loan_amount / n
    return loan_amount * r / (1 - (1 + r) ** -n)


def remaining_balance(loan_amount: float, annual_rate_pct: float, term_years: int, months_elapsed: int) -> float:
    n = term_years * 12
    r = annual_rate_pct / 100 / 12
    months_elapsed = min(months_elapsed, n)
    payment = monthly_payment(loan_amount, annual_rate_pct, term_years)
    if r == 0:
        return max(loan_amount - payment * months_elapsed, 0.0)
    balance = loan_amount * (1 + r) ** months_elapsed - payment * (((1 + r) ** months_elapsed - 1) / r)
    return max(balance, 0.0)
