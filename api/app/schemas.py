from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, Field


class InvoiceOut(BaseModel):
    id: int
    source: str
    paperless_doc_id: int
    paperless_created: datetime.datetime | None = None
    title: str | None = None
    vendor: str | None = None
    amount: float | None = None
    currency: str
    confidence: float
    needs_review: bool
    extracted_at: datetime.datetime
    updated_at: datetime.datetime
    debug_json: str | None = None
    correspondent: str | None = None
    document_type: str | None = None
    ocr_text: str | None = None
    ocr_snippet: str | None = None

    model_config = {'from_attributes': True}


class InvoiceUpdate(BaseModel):
    vendor: str | None = None
    amount: float | None = None
    needs_review: bool | None = None


class ManualCostCreate(BaseModel):
    date: datetime.date | None = None
    vendor: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: str = 'EUR'
    category: str | None = None
    note: str | None = None


class ManualCostUpdate(BaseModel):
    date: datetime.date | None = None
    vendor: str | None = None
    amount: float | None = Field(default=None, gt=0)
    currency: str | None = None
    category: str | None = None
    note: str | None = None


class ManualCostOut(BaseModel):
    id: int
    source: str
    date: datetime.date
    vendor: str
    amount: float
    currency: str
    category: str | None = None
    note: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {'from_attributes': True}


class SyncResponse(BaseModel):
    synced: int
    inserted: int
    updated: int
    skipped: int
    pool_tag_id: int


class KeyValueAmount(BaseModel):
    name: str
    amount: float


class CategoryAmount(BaseModel):
    category: str
    amount: float


class SummaryOut(BaseModel):
    total_amount: float
    paperless_total: float
    manual_total: float
    invoice_count: int
    manual_cost_count: int
    needs_review_count: int
    top_vendors: list[KeyValueAmount]
    costs_by_category: list[CategoryAmount]


class ConfigOut(BaseModel):
    paperless_base_url: str
    pool_tag_name: str
    scheduler_enabled: bool
    scheduler_interval_minutes: int
    scheduler_run_on_startup: bool


class AllCostRow(BaseModel):
    date: str | None
    source: str
    vendor: str | None
    amount: float | None
    currency: str | None
    title: str | None
    category: str | None
    note: str | None
    paperless_doc_id: int | None
    confidence: float | None
    needs_review: bool | None


class ExtractionDebug(BaseModel):
    keyword: str | None = None
    regex: str | None = None
    context_snippet: str | None = None
    vendor_source: str | None = None
    candidates_checked: int | None = None
    extra: dict[str, Any] | None = None
