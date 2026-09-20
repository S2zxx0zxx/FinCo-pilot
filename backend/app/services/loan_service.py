import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.schemas.loan import LoanCreate, LoanInstallment

CENT = Decimal("0.01")


def amortize(loan: LoanCreate) -> list[LoanInstallment]:
    """Monthly reducing-balance estimate, rounding each cash flow to cents.

    Preserve the original day (or month-end), including leap years. No fees,
    daily accrual, floating rates, partial repayments or prepayments are inferred.
    """
    with localcontext() as context:
        context.prec = 40
        rate = loan.annual_rate / Decimal(1200)
        principal = loan.principal
        payment = (
            principal / loan.term_months if not rate
            else principal * rate / (1 - (1 + rate) ** (-loan.term_months))
        ).quantize(CENT, rounding=ROUND_HALF_UP)
        # Tiny loans must amortize even when the formula rounds below one cent.
        payment = max(CENT, payment)
        balance = principal
        first = loan.first_due_date
        end_of_month = first.day == calendar.monthrange(first.year, first.month)[1]
        schedule = []
        for index in range(loan.term_months):
            year, month = divmod(first.year * 12 + first.month - 1 + index, 12)
            month += 1
            last = calendar.monthrange(year, month)[1]
            due = date(year, month, last if end_of_month else min(first.day, last))
            interest = (balance * rate).quantize(CENT, rounding=ROUND_HALF_UP)
            principal_part = min(balance, max(Decimal(0), payment - interest))
            if index == loan.term_months - 1:
                principal_part = balance
            balance -= principal_part
            schedule.append(LoanInstallment(
                number=index + 1, due_date=due,
                payment=principal_part + interest, principal=principal_part,
                interest=interest, remaining_principal=balance,
                reported_paid=index < loan.paid_installments,
            ))
        return schedule
