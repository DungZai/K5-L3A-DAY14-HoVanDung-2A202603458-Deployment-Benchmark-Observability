"""Enforce the daily mock LLM budget across all agent workers."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from utils.mock_llm import MOCK_RESPONSES

from .config import settings
from .redis_client import r


NANO_USD_PER_USD = 1_000_000_000
# $0.00015 per 1,000 input tokens and $0.00060 per 1,000 output tokens.
PRICE_INPUT_NANO_USD = 150
PRICE_OUTPUT_NANO_USD = 600

RESERVE_BUDGET = r.register_script("""
local spent = tonumber(redis.call('GET', KEYS[1]) or '0')
local amount = tonumber(ARGV[1])
if spent + amount > tonumber(ARGV[2]) then
    return 0
end

redis.call('INCRBY', KEYS[1], amount)
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return 1
""")

RELEASE_BUDGET = r.register_script("""
-- A request can finish after midnight, when its budget key has expired.
if redis.call('EXISTS', KEYS[1]) == 1 then
    redis.call('DECRBY', KEYS[1], ARGV[1])
end
""")


@dataclass(frozen=True)
class BudgetReservation:
    key: str
    amount: int


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


MAX_OUTPUT_TOKENS = max(
    estimate_tokens(answer) for answers in MOCK_RESPONSES.values() for answer in answers
)


def check_budget(input_tokens: int) -> BudgetReservation:
    """Reserve enough for the longest mock answer before invoking the LLM."""
    now = datetime.now(timezone.utc)
    reset_at = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    reservation = BudgetReservation(
        key=f"day14:budget:{now.date().isoformat()}",
        amount=input_tokens * PRICE_INPUT_NANO_USD + MAX_OUTPUT_TOKENS * PRICE_OUTPUT_NANO_USD,
    )
    approved = RESERVE_BUDGET(
        keys=[reservation.key],
        args=[
            reservation.amount,
            int(settings.daily_budget_usd * NANO_USD_PER_USD),
            int(reset_at.timestamp()),
        ],
    )
    if not approved:
        raise HTTPException(status_code=402, detail="Daily LLM budget exceeded")
    return reservation


def cancel_cost(reservation: BudgetReservation) -> None:
    RELEASE_BUDGET(keys=[reservation.key], args=[reservation.amount])


def record_cost(reservation: BudgetReservation, input_tokens: int, output_tokens: int) -> float:
    """Keep the actual token cost and release any unused reservation."""
    actual = input_tokens * PRICE_INPUT_NANO_USD + output_tokens * PRICE_OUTPUT_NANO_USD
    RELEASE_BUDGET(keys=[reservation.key], args=[reservation.amount - actual])
    return actual / NANO_USD_PER_USD
