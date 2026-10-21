"""A shared run ledger; a request is reserved before dispatch, including every retry."""

from decimal import Decimal, InvalidOperation


class BudgetError(Exception):
    pass


class RunBudget:
    def __init__(self, settings, spent=0):
        # User policy is permanent free-only, even if a caller bypasses settings validation.
        self.allow_paid = False
        self.limit = Decimal(0)
        self.spent = Decimal(str(spent))
        if not self.spent.is_finite() or self.spent < 0 or self.spent > self.limit:
            raise BudgetError("INVALID_RUN_COST")

    def check(self, cost, paid_provider=False):
        if paid_provider and not self.allow_paid:
            raise BudgetError("PAID_PROVIDERS_DISABLED")
        if cost is None:
            raise BudgetError("REQUEST_PRICE_UNKNOWN")
        try:
            amount = Decimal(str(cost))
        except InvalidOperation:
            raise BudgetError("INVALID_REQUEST_PRICE") from None
        if not amount.is_finite() or amount < 0:
            raise BudgetError("INVALID_REQUEST_PRICE")
        if amount > 0 and not self.allow_paid:
            raise BudgetError("PAID_PROVIDERS_DISABLED")
        if self.spent + amount > self.limit:
            raise BudgetError("COST_BUDGET_EXHAUSTED")
        return amount

    def reserve(self, cost, paid_provider=False):
        # No await: checking and reserving are atomic within the async event loop.
        self.spent += self.check(cost, paid_provider)
