from __future__ import annotations

import json
import re
from dataclasses import dataclass

POSITIVE_KEYWORDS = [
    'zahlbetrag',
    'zu zahlen',
    'endbetrag',
    'rechnungsbetrag',
    'gesamtbetrag',
    'bruttobetrag',
    'brutto',
    'total',
    'gesamt',
    'summe',
    'betrag',
]

NEGATIVE_KEYWORDS = [
    'rabatt',
    'skonto',
    'nachlass',
    'gutschrift',
    'ersparnis',
    'bonus',
    'preisvorteil',
    'discount',
]

NEUTRAL_KEYWORDS = [
    'netto',
    'mwst',
    'ust',
    'steuer',
    'mehrwertsteuer',
    'zwischen',
    'zwischenbetrag',
    'zwischensumme',
]

LETTER_CLASS = 'A-Za-zÄÖÜäöüß'
AMOUNT_REGEX = r'(?P<amount>(?:\d{1,3}(?:[.\s]\d{3})+|\d+)(?:,\d{2}|\.\d{2})?|\d+)'
AMOUNT_PATTERN = re.compile(AMOUNT_REGEX + r'(?:\s?(?:EUR|€))?', flags=re.IGNORECASE)
EMAIL_RE = re.compile(r'\b[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}\b')
ARTIFACT_RE = re.compile(
    r'\b(?:rechnung|invoice|datum|date|iban|bic|ust\.?-?id|ust-idnr|tel\.?|telefon|fax|email|e-mail|www\.|http|kundennr|kundennummer|steuer|seite)\b',
    re.IGNORECASE,
)


@dataclass
class AmountCandidate:
    amount: float
    raw: str
    line_index: int
    line_text: str
    start: int
    end: int
    context: str
    has_currency_nearby: bool
    is_negative: bool
    pos_same_line: list[str]
    pos_context: list[str]
    neg_same_line: list[str]
    neg_context: list[str]
    neutral_same_line: list[str]
    neutral_context: list[str]
    score: int


@dataclass
class VendorCandidate:
    value: str | None
    source: str


def parse_eur_amount(raw: str) -> float | None:
    value = raw.strip().replace('€', '').replace('EUR', '').replace('eur', '').strip()
    if not value:
        return None

    value = re.sub(r'(?<=\d)\s+(?=\d)', '', value)

    if ',' in value and '.' in value:
        if value.rfind(',') > value.rfind('.'):
            normalized = value.replace('.', '').replace(',', '.')
        else:
            normalized = value.replace(',', '')
    elif ',' in value and ' ' in value:
        normalized = value.replace(' ', '').replace(',', '.')
    elif ',' in value:
        normalized = value.replace(' ', '').replace('.', '').replace(',', '.')
    else:
        normalized = value.replace(' ', '')

    try:
        return round(float(normalized), 2)
    except ValueError:
        return None


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword).replace(r'\ ', r'\s+')
    return re.compile(rf'(?<![{LETTER_CLASS}]){escaped}(?![{LETTER_CLASS}])', re.IGNORECASE)


def _normalize_lines(text: str) -> list[str]:
    return [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]


def _find_keywords(text: str, keywords: list[str]) -> list[str]:
    low = text.lower()
    found: list[str] = []
    for keyword in keywords:
        if _keyword_pattern(keyword).search(low):
            found.append(keyword)
    return found


def _line_start_indices(lines: list[str], source_text: str) -> list[int]:
    starts: list[int] = []
    cursor = 0
    for line in lines:
        idx = source_text.find(line, cursor)
        if idx == -1:
            idx = cursor
        starts.append(idx)
        cursor = idx + len(line)
    return starts


def _currency_near(text: str, start: int, end: int) -> bool:
    left = max(0, start - 10)
    right = min(len(text), end + 10)
    nearby = text[left:right]
    return bool(re.search(r'(€|\bEUR\b)', nearby, flags=re.IGNORECASE))


def _is_negative_near(text: str, start: int, end: int) -> bool:
    left = max(0, start - 4)
    right = min(len(text), end + 2)
    nearby = text[left:right]
    left_side = nearby[: start - left]
    compact_left = re.sub(r'\s+', '', left_side)
    return compact_left.endswith('-') or compact_left.endswith('−') or compact_left.endswith('(')


def _score_candidate(candidate: AmountCandidate) -> int:
    score = 0
    if candidate.pos_same_line:
        score += 40
    if candidate.pos_context:
        score += 25
    if candidate.neg_same_line:
        score -= 60
    if candidate.neg_context:
        score -= 35
    if candidate.neutral_same_line:
        score -= 15
    if candidate.has_currency_nearby:
        score += 10
    if candidate.is_negative:
        score -= 50
    return score


def _amount_candidates(text: str) -> list[AmountCandidate]:
    lines = _normalize_lines(text)
    if not lines:
        return []

    starts = _line_start_indices(lines, text)
    candidates: list[AmountCandidate] = []

    for line_idx, line in enumerate(lines):
        line_start = starts[line_idx]
        line_end = line_start + len(line)
        for match in AMOUNT_PATTERN.finditer(line):
            raw = match.group('amount')
            amount = parse_eur_amount(raw)
            if amount is None:
                continue

            global_start = line_start + match.start('amount')
            global_end = line_start + match.end('amount')
            context_left = max(0, global_start - 60)
            context_right = min(len(text), global_end + 60)
            context = text[context_left:context_right]

            pos_same = _find_keywords(line, POSITIVE_KEYWORDS)
            pos_context = _find_keywords(context, POSITIVE_KEYWORDS)
            neg_same = _find_keywords(line, NEGATIVE_KEYWORDS)
            neg_context = _find_keywords(context, NEGATIVE_KEYWORDS)
            neutral_same = _find_keywords(line, NEUTRAL_KEYWORDS)
            neutral_context = _find_keywords(context, NEUTRAL_KEYWORDS)
            has_currency_nearby = _currency_near(text, global_start, global_end)
            is_negative = _is_negative_near(text, global_start, global_end)

            if ',' not in raw and '.' not in raw and not has_currency_nearby:
                continue

            candidate = AmountCandidate(
                amount=amount,
                raw=raw,
                line_index=line_idx,
                line_text=line,
                start=global_start,
                end=global_end,
                context=context,
                has_currency_nearby=has_currency_nearby,
                is_negative=is_negative,
                pos_same_line=pos_same,
                pos_context=pos_context,
                neg_same_line=neg_same,
                neg_context=neg_context,
                neutral_same_line=neutral_same,
                neutral_context=neutral_context,
                score=0,
            )
            candidate.score = _score_candidate(candidate)

            # Plausibility constraints
            if candidate.amount <= 0 or candidate.amount > 1_000_000:
                continue

            candidates.append(candidate)

    return candidates


def _choose_candidate(candidates: list[AmountCandidate]) -> AmountCandidate | None:
    if not candidates:
        return None

    def tie_amount(c: AmountCandidate) -> float:
        return c.amount if not c.neg_same_line else 0.0

    return max(
        candidates,
        key=lambda c: (
            c.score,
            bool(c.pos_same_line),
            tie_amount(c),
            -c.line_index,
        ),
    )


def _pick_vendor(text: str, correspondent: str | None) -> VendorCandidate:
    if correspondent and str(correspondent).strip():
        return VendorCandidate(str(correspondent).strip()[:255], 'correspondent')

    lines = _normalize_lines(text)[:8]
    for line in lines:
        lower = line.lower()
        if len(line) < 3 or len(line) > 90:
            continue
        if any(_keyword_pattern(keyword).search(lower) for keyword in POSITIVE_KEYWORDS):
            continue
        if AMOUNT_PATTERN.search(line):
            continue
        if EMAIL_RE.search(line):
            continue
        if ARTIFACT_RE.search(lower):
            continue
        if re.search(r'\b\d{5}\b', line):
            continue
        if re.search(r'^(?:[A-Z]{2}\d|DE\d{2})', line):
            continue
        if re.fullmatch(r'[\d\s+\-./]+', line):
            continue
        return VendorCandidate(line[:255], 'ocr_heuristic')

    return VendorCandidate(None, 'none')


def _build_debug_top(candidates: list[AmountCandidate]) -> list[dict]:
    ranked = sorted(
        candidates,
        key=lambda c: (c.score, bool(c.pos_same_line), c.amount, -c.line_index),
        reverse=True,
    )[:5]
    top: list[dict] = []
    for c in ranked:
        matched_keywords = {
            'positive': sorted(set(c.pos_same_line + c.pos_context)),
            'negative': sorted(set(c.neg_same_line + c.neg_context)),
            'neutral': sorted(set(c.neutral_same_line + c.neutral_context)),
        }
        top.append(
            {
                'value': c.amount,
                'score': c.score,
                'line_snippet': c.line_text[:120],
                'matched_keywords': matched_keywords,
            }
        )
    return top


def extract_invoice_fields(text: str, correspondent: str | None) -> dict:
    text = text or ''
    vendor_candidate = _pick_vendor(text, correspondent)
    candidates = _amount_candidates(text)
    chosen = _choose_candidate(candidates)

    amount = chosen.amount if chosen and not chosen.is_negative else None

    low_signal = chosen is None or chosen.score < 25
    only_neutral = bool(
        chosen
        and not chosen.pos_same_line
        and not chosen.pos_context
        and (chosen.neutral_same_line or chosen.neutral_context)
    )
    needs_review_amount = low_signal or only_neutral
    needs_review = needs_review_amount or not vendor_candidate.value

    confidence = 0.15
    if vendor_candidate.value:
        confidence += 0.3 if vendor_candidate.source == 'correspondent' else 0.2
    if chosen:
        confidence += min(max(chosen.score, 0), 80) / 180.0
        if chosen.pos_same_line:
            confidence += 0.1
        elif chosen.pos_context:
            confidence += 0.05
    if needs_review:
        confidence = min(confidence, 0.64)
    confidence = round(min(confidence, 0.99), 2)

    context_snippet = chosen.context[:500] if chosen else None

    debug = {
        'keyword': chosen.pos_same_line[0] if chosen and chosen.pos_same_line else (chosen.pos_context[0] if chosen and chosen.pos_context else None),
        'regex': AMOUNT_REGEX,
        'context_snippet': context_snippet,
        'vendor_source': vendor_candidate.source,
        'candidates_checked': len(candidates),
        'top_candidates': _build_debug_top(candidates),
        'extra': {
            'chosen_raw': chosen.raw if chosen else None,
            'chosen_score': chosen.score if chosen else None,
            'chosen_line': chosen.line_text[:200] if chosen else None,
            'chosen_is_negative': chosen.is_negative if chosen else None,
            'needs_review_amount_reason': {
                'low_signal': low_signal,
                'only_neutral': only_neutral,
            },
        },
    }

    return {
        'vendor': vendor_candidate.value,
        'amount': amount,
        'currency': 'EUR',
        'confidence': confidence,
        'needs_review': needs_review,
        'debug_json': json.dumps(debug, ensure_ascii=True),
    }
