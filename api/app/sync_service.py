from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .extraction import extract_invoice_fields
from .models import Invoice
from .paperless import PaperlessClient
from .schemas import SyncResponse
from .settings import Settings


async def sync_invoices(db: Session, settings: Settings) -> SyncResponse:
    client = PaperlessClient(settings)
    project_tag_id = await client.get_tag_id_by_name()
    docs = await client.get_project_documents(project_tag_id)

    existing = {}
    if docs:
        doc_ids = [int(doc['id']) for doc in docs if doc.get('id') is not None]
        if doc_ids:
            existing = {
                row.paperless_doc_id: row
                for row in db.scalars(select(Invoice).where(Invoice.paperless_doc_id.in_(doc_ids))).all()
            }

    inserted = updated = skipped = 0
    now = datetime.utcnow()

    for doc in docs:
        if doc.get('id') is None:
            continue
        extracted = extract_invoice_fields(doc.get('content') or '', doc.get('correspondent'))
        inv = existing.get(int(doc['id']))

        paperless_created = None
        if doc.get('created'):
            try:
                paperless_created = datetime.fromisoformat(str(doc['created']).replace('Z', '+00:00'))
            except ValueError:
                paperless_created = None

        new_data = {
            'source': 'paperless',
            'paperless_doc_id': int(doc['id']),
            'paperless_created': paperless_created,
            'title': doc.get('title'),
            'currency': extracted.get('currency', 'EUR'),
            'confidence': float(extracted.get('confidence') or 0.0),
            'extracted_at': now,
            'debug_json': extracted.get('debug_json'),
            'correspondent': doc.get('correspondent'),
            'document_type': doc.get('document_type'),
            'ocr_text': doc.get('content') or '',
        }

        if inv is None:
            new_data['vendor'] = extracted.get('vendor')
            new_data['amount'] = Decimal(str(extracted['amount'])) if extracted.get('amount') is not None else None
            new_data['vendor_source'] = 'auto'
            new_data['amount_source'] = 'auto'
            new_data['needs_review'] = bool(extracted.get('needs_review', True))
            db.add(Invoice(**new_data))
            inserted += 1
            continue

        changed = False
        extracted_vendor = extracted.get('vendor')
        extracted_amount = Decimal(str(extracted['amount'])) if extracted.get('amount') is not None else None

        if inv.vendor_source == 'auto':
            new_data['vendor'] = extracted_vendor
        if inv.amount_source == 'auto':
            new_data['amount'] = extracted_amount

        # Manual overrides should not be reverted to review-required by sync.
        if inv.vendor_source == 'manual' or inv.amount_source == 'manual':
            new_data['needs_review'] = False
        else:
            new_data['needs_review'] = bool(extracted.get('needs_review', True))

        for key, value in new_data.items():
            if getattr(inv, key) != value:
                setattr(inv, key, value)
                changed = True
        if changed:
            updated += 1
        else:
            skipped += 1

    db.commit()
    return SyncResponse(synced=len(docs), inserted=inserted, updated=updated, skipped=skipped, pool_tag_id=project_tag_id)
