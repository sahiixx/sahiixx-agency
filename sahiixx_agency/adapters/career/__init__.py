"""Career-Ops adapter package."""

from sahiixx_agency.adapters.career.career_ops_adapter import (
    CareerOpsAdapter,
    CareerOpsResult,
    run_cops_oferta,
)
from sahiixx_agency.adapters.career.telegram_dispatcher import (
    CareerOpsDispatcher,
    CareerOpsTelegramBot,
    DispatchResult,
    run_bot,
)

__all__ = [
    "CareerOpsAdapter",
    "CareerOpsDispatcher",
    "CareerOpsTelegramBot",
    "CareerOpsResult",
    "DispatchResult",
    "run_bot",
    "run_cops_oferta",
]
