"""The shapes of the UnderCover API."""

from typing import Literal, Self

from pydantic import BaseModel, model_validator

Status = Literal["waiting", "in_progress", "waiting_for_sign_off", "decided"]
Outcome = Literal["approve", "decline", "refer"]
StepKind = Literal["call", "result", "message"]


class Decision(BaseModel):
    outcome: Outcome
    payout: float
    reason: str
    policy_section: str

    @model_validator(mode="after")
    def payout_fits_outcome(self) -> Self:
        """Check that an approve pays something and a decline or refer pays nothing."""
        if self.outcome == "approve" and self.payout <= 0:
            raise ValueError("An approve needs a payout above $0")
        if self.outcome != "approve" and self.payout != 0:
            raise ValueError(f"A {self.outcome} needs a payout of $0")
        return self


class Payment(BaseModel):
    amount: float


class SignOff(BaseModel):
    handler_id: str


class NewStep(BaseModel):
    thread_id: str
    kind: StepKind
    name: str
    content: str


class Step(NewStep):
    id: int
    created_at: str


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class RecordedDecision(BaseModel):
    outcome: Outcome
    payout: float
    reason: str
    policy_section: str
    decided_at: str


class RecordedSignOff(BaseModel):
    handler_id: str
    handler_name: str
    signed_off_at: str


class RecordedPayment(BaseModel):
    amount: float
    paid_at: str


class ClaimSummary(BaseModel):
    claim_id: str
    customer_name: str
    claim_type: str
    summary: str
    submitted_on: str
    amount_claimed: float
    status: Status
    outcome: Outcome | None
    payout: float | None
    paid: bool


class Claim(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    claim_type: str
    submitted_on: str
    incident_date: str
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: float
    documents: list[Document]
    status: Status
    decision: RecordedDecision | None
    sign_off: RecordedSignOff | None
    payment: RecordedPayment | None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class ClaimHistory(BaseModel):
    customer_id: str
    name: str
    customer_since: str
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class Instructions(BaseModel):
    instructions: str
