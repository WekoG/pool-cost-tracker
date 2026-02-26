from __future__ import annotations

from sqlalchemy import cast, literal, select, union_all
from sqlalchemy.sql.sqltypes import String

from .models import Invoice, ManualCost


def all_costs_union_query():
    invoice_query = select(
        cast(Invoice.paperless_created, String).label('date'),
        Invoice.source.label('source'),
        Invoice.vendor.label('vendor'),
        Invoice.amount.label('amount'),
        Invoice.currency.label('currency'),
        Invoice.title.label('title'),
        literal(None).label('category'),
        literal(None).label('note'),
        Invoice.paperless_doc_id.label('paperless_doc_id'),
        Invoice.confidence.label('confidence'),
        Invoice.needs_review.label('needs_review'),
    )

    manual_query = select(
        cast(ManualCost.date, String).label('date'),
        ManualCost.source.label('source'),
        ManualCost.vendor.label('vendor'),
        ManualCost.amount.label('amount'),
        ManualCost.currency.label('currency'),
        literal(None).label('title'),
        ManualCost.category.label('category'),
        ManualCost.note.label('note'),
        literal(None).label('paperless_doc_id'),
        literal(None).label('confidence'),
        literal(None).label('needs_review'),
    )

    return union_all(invoice_query, manual_query)
