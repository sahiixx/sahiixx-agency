"""Read-only command-center API for the Panac enterprise intelligence MVP."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/panac", tags=["panac"])


class Metric(BaseModel):
    label: str
    value: str
    change: str
    trend: Literal["up", "down", "neutral"]
    detail: str


class BusinessSignal(BaseModel):
    id: str
    domain: Literal["revenue", "forecast", "inventory", "retention", "compliance", "risk"]
    title: str
    detail: str
    severity: Literal["critical", "high", "medium", "low"]
    impact: str


class Recommendation(BaseModel):
    id: str
    title: str
    owner: str
    domain: str
    expected_impact: str
    rationale: str
    status: Literal["review", "approved"] = "review"
    requires_approval: bool = True


class PanacOverview(BaseModel):
    workspace: str
    period: str
    metrics: list[Metric]
    signals: list[BusinessSignal]
    recommendations: list[Recommendation]
    agents: list[str]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    demo_mode: bool = True


class ImportRequest(BaseModel):
    source: Literal["contracts", "subscriptions", "usage", "inventory"]
    records: list[dict[str, str | int | float | bool | None]] = Field(min_length=1, max_length=10_000)


class ImportSummary(BaseModel):
    source: str
    records_imported: int
    imported_at: datetime
    status: Literal["ready"] = "ready"


class RecognitionSchedule(BaseModel):
    contract_id: str
    customer: str
    contract_value: float
    recognized_value: float
    deferred_value: float
    status: Literal["not_started", "active", "completed", "review_required"]
    review_reason: str


class RevenueRecognitionOverview(BaseModel):
    as_of: date
    contract_value: float
    recognized_value: float
    deferred_value: float
    schedules: list[RecognitionSchedule]
    disclaimer: str


class DemandForecast(BaseModel):
    sku: str
    daily_demand: float
    projected_30_day_demand: float
    available_inventory: float
    coverage_days: float | None
    risk: Literal["critical", "high", "medium", "low"]


class DemandPlanningOverview(BaseModel):
    horizon_days: int
    forecasts: list[DemandForecast]
    disclaimer: str


_REQUIRED_COLUMNS = {
    "contracts": {"contract_id", "customer", "start_date", "end_date", "value"},
    "subscriptions": {"subscription_id", "customer", "plan", "mrr"},
    "usage": {"account_id", "date", "metric", "quantity"},
    "inventory": {"sku", "location", "available_quantity"},
}


def _number(value: object) -> float:
    """Return a non-negative number from a connector or CSV value."""
    try:
        return max(float(str(value).replace(",", "").replace("$", "")), 0)
    except (TypeError, ValueError):
        return 0.0


def _records_for_source(request: Request, source: str) -> list[dict[str, object]]:
    extract = request.app.state.panac_memory.get(f"panac:source:{source}", {})
    records = extract.get("records", []) if isinstance(extract, dict) else []
    return records if isinstance(records, list) else []


def _connected_metrics(request: Request) -> list[Metric]:
    contracts = _records_for_source(request, "contracts")
    subscriptions = _records_for_source(request, "subscriptions")
    usage = _records_for_source(request, "usage")
    inventory = _records_for_source(request, "inventory")
    return [
        Metric(label="Imported contract value", value=f"${sum(_number(row.get('value')) for row in contracts):,.0f}", change=f"{len(contracts)} contracts", trend="neutral", detail="from imported extracts"),
        Metric(label="Subscription MRR", value=f"${sum(_number(row.get('mrr')) for row in subscriptions):,.0f}", change=f"{len(subscriptions)} subscriptions", trend="neutral", detail="from imported extracts"),
        Metric(label="Tracked usage", value=f"{sum(_number(row.get('quantity')) for row in usage):,.0f}", change=f"{len(usage)} events", trend="neutral", detail="from imported extracts"),
        Metric(label="Available inventory", value=f"{sum(_number(row.get('available_quantity')) for row in inventory):,.0f}", change=f"{len(inventory)} stock records", trend="neutral", detail="from imported extracts"),
    ]


def _revenue_schedule(record: dict[str, object], as_of: date) -> RecognitionSchedule:
    contract_id = str(record.get("contract_id", "Unknown contract"))
    customer = str(record.get("customer", "Unknown customer"))
    value = _number(record.get("value"))
    try:
        start = date.fromisoformat(str(record.get("start_date")))
        end = date.fromisoformat(str(record.get("end_date")))
        if end < start:
            raise ValueError
    except ValueError:
        return RecognitionSchedule(contract_id=contract_id, customer=customer, contract_value=value, recognized_value=0, deferred_value=value, status="review_required", review_reason="Invalid contract start or end date.")

    if as_of < start:
        return RecognitionSchedule(contract_id=contract_id, customer=customer, contract_value=value, recognized_value=0, deferred_value=value, status="not_started", review_reason="Recognition has not started.")
    if as_of >= end:
        return RecognitionSchedule(contract_id=contract_id, customer=customer, contract_value=value, recognized_value=value, deferred_value=0, status="completed", review_reason="Schedule complete; review modifications before posting.")
    elapsed_days = (as_of - start).days + 1
    total_days = (end - start).days + 1
    recognized = round(value * elapsed_days / total_days, 2)
    return RecognitionSchedule(contract_id=contract_id, customer=customer, contract_value=value, recognized_value=recognized, deferred_value=round(value - recognized, 2), status="active", review_reason="Straight-line estimate; verify performance obligations, variable consideration, and modifications.")


def _demand_forecasts(request: Request) -> list[DemandForecast]:
    demand_by_sku: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    for row in _records_for_source(request, "usage"):
        try:
            observed_on = date.fromisoformat(str(row.get("date")))
        except ValueError:
            continue
        demand_by_sku[str(row.get("metric", "Unknown metric"))][observed_on] += _number(row.get("quantity"))
    inventory_by_sku: dict[str, float] = defaultdict(float)
    for row in _records_for_source(request, "inventory"):
        inventory_by_sku[str(row.get("sku", "Unknown SKU"))] += _number(row.get("available_quantity"))

    forecasts: list[DemandForecast] = []
    for sku in sorted(set(demand_by_sku) | set(inventory_by_sku)):
        observations = demand_by_sku[sku]
        total_usage = sum(observations.values())
        observed_days = (max(observations) - min(observations)).days + 1 if observations else 0
        daily_demand = total_usage / observed_days if observed_days else 0
        available = inventory_by_sku[sku]
        coverage_days = round(available / daily_demand, 1) if daily_demand else None
        risk = "low" if coverage_days is None or coverage_days >= 45 else "medium" if coverage_days >= 30 else "high" if coverage_days >= 14 else "critical"
        forecasts.append(DemandForecast(sku=sku, daily_demand=round(daily_demand, 2), projected_30_day_demand=round(daily_demand * 30, 2), available_inventory=available, coverage_days=coverage_days, risk=risk))
    return forecasts


_RECOMMENDATIONS = [
    Recommendation(
        id="rec_price_001",
        title="Protect renewal margin for high-usage accounts",
        owner="Revenue strategy agent",
        domain="Pricing & retention",
        expected_impact="+$184k annualized gross margin",
        rationale="Usage is 34% above contracted capacity across 18 accounts; renewal windows open in 45 days.",
    ),
    Recommendation(
        id="rec_inventory_001",
        title="Rebalance constrained inventory to priority channel",
        owner="Demand & inventory agent",
        domain="Inventory",
        expected_impact="Avoid $96k at-risk revenue",
        rationale="Forecasted demand exceeds available supply in the enterprise channel during the next planning cycle.",
    ),
    Recommendation(
        id="rec_revenue_001",
        title="Review modified contract revenue allocation",
        owner="Revenue recognition agent",
        domain="ASC 606",
        expected_impact="Reduce close risk on $420k contract value",
        rationale="A contract modification requires review of performance obligations and transaction-price allocation.",
    ),
]


@router.get("/overview", response_model=PanacOverview)
async def overview(request: Request) -> PanacOverview:
    """Return a safe, seeded workspace until customer systems are connected."""
    import_summaries = request.app.state.panac_memory.get("panac:imports", [])
    metrics = _connected_metrics(request) if import_summaries else [
        Metric(label="Annual recurring revenue", value="$12.48M", change="+12.4%", trend="up", detail="vs. prior year"),
        Metric(label="Net revenue retention", value="113.8%", change="+3.1 pts", trend="up", detail="trailing 12 months"),
        Metric(label="Forecast confidence", value="87%", change="+5 pts", trend="up", detail="next 90 days"),
        Metric(label="Deferred revenue", value="$3.16M", change="+8.2%", trend="neutral", detail="contracted balance"),
    ]
    return PanacOverview(
        workspace="Northstar Industries",
        period="Q3 operating view",
        metrics=metrics,
        signals=[
            BusinessSignal(id="sig_000", domain="revenue", title="Expansion opportunity identified", detail="High-adoption accounts are approaching contracted usage thresholds ahead of their renewal windows.", severity="medium", impact="+$184k annualized margin opportunity"),
            BusinessSignal(id="sig_001", domain="risk", title="Renewal concentration", detail="Three strategic renewals represent 19% of the next-quarter renewal base.", severity="high", impact="$612k exposed ARR"),
            BusinessSignal(id="sig_002", domain="inventory", title="Supply constraint projected", detail="Enterprise channel inventory is projected to fall below its service threshold in 21 days.", severity="medium", impact="$96k revenue at risk"),
            BusinessSignal(id="sig_003", domain="compliance", title="Contract modification awaiting review", detail="One modified agreement needs performance-obligation review before the close.", severity="high", impact="$420k contract value"),
            BusinessSignal(id="sig_004", domain="forecast", title="Demand signal improving", detail="Qualified pipeline and product usage indicate upside in the mid-market segment.", severity="low", impact="+$240k forecast upside"),
        ],
        recommendations=_RECOMMENDATIONS,
        agents=[
            "Revenue intelligence",
            "Pricing optimization",
            "Forecasting",
            "Contract & ASC 606 review",
            "Demand & inventory",
            "Retention & risk",
        ],
        demo_mode=not bool(import_summaries),
    )


@router.get("/imports", response_model=list[ImportSummary])
async def list_imports(request: Request) -> list[ImportSummary]:
    return [ImportSummary.model_validate(item) for item in request.app.state.panac_memory.get("panac:imports", [])]


@router.get("/revenue-recognition", response_model=RevenueRecognitionOverview)
async def revenue_recognition(request: Request, as_of: date | None = None) -> RevenueRecognitionOverview:
    """Generate a review-only schedule from imported contracts; never create journal entries."""
    effective_date = as_of or date.today()
    schedules = [_revenue_schedule(record, effective_date) for record in _records_for_source(request, "contracts")]
    return RevenueRecognitionOverview(
        as_of=effective_date,
        contract_value=round(sum(item.contract_value for item in schedules), 2),
        recognized_value=round(sum(item.recognized_value for item in schedules), 2),
        deferred_value=round(sum(item.deferred_value for item in schedules), 2),
        schedules=schedules,
        disclaimer="Review-only straight-line estimate. This is not an ASC 606 determination or an accounting posting.",
    )


@router.get("/demand-planning", response_model=DemandPlanningOverview)
async def demand_planning(request: Request) -> DemandPlanningOverview:
    """Project short-term demand from imported usage and flag inventory coverage risks."""
    return DemandPlanningOverview(horizon_days=30, forecasts=_demand_forecasts(request), disclaimer="Planning estimate only. Usage metric values must match inventory SKUs for coverage calculations.")


@router.post("/imports", response_model=ImportSummary, status_code=201)
async def import_records(payload: ImportRequest, request: Request) -> ImportSummary:
    """Validate and retain a source extract; no source records are sent to third parties."""
    available_columns = set().union(*(record.keys() for record in payload.records))
    missing = _REQUIRED_COLUMNS[payload.source] - available_columns
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required columns: {', '.join(sorted(missing))}")

    summary = ImportSummary(source=payload.source, records_imported=len(payload.records), imported_at=datetime.now(UTC))
    memory = request.app.state.panac_memory
    memory.set(f"panac:source:{payload.source}", payload.model_dump(mode="json"))
    summaries = [item for item in memory.get("panac:imports", []) if item["source"] != payload.source]
    summaries.append(summary.model_dump(mode="json"))
    memory.set("panac:imports", summaries)
    memory.log_event("panac.imported", summary.model_dump(mode="json"))
    return summary


@router.post("/recommendations/{recommendation_id}/approve", response_model=Recommendation)
async def approve_recommendation(recommendation_id: str) -> Recommendation:
    """Record an operator decision only; this MVP never writes to business systems."""
    for recommendation in _RECOMMENDATIONS:
        if recommendation.id == recommendation_id:
            recommendation.status = "approved"
            return recommendation
    raise HTTPException(status_code=404, detail="Recommendation not found")
