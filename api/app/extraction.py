from __future__ import annotations

import json
import re
from dataclasses import dataclass

AMOUNT_KEYWORDS = [
    'rechnungsbetrag',
    'gesamt',
    'summe',
    'total',
    'brutto',
    'endbetrag',
    'zahlbetrag',
    'zu zahlen',
]

LETTER_CLASS = 'A-Za-zÄÖÜäöüß'
AMOUNT_REGEX = r'(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2}|\d+)'
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
    score: float
    keyword: str | None
    proximity: int | None


@dataclass
class VendorCandidate:
    value: str | None
    source: str



def parse_eur_amount(raw: str) -> float | None:
    value = raw.strip().replace('€', '').replace('EUR', '').replace('eur', '').strip()
    if not value:
        return None

    if ',' in value and '.' in value:
        if value.rfind(',') > value.rfind('.'):
            normalized = value.replace('.', '').replace(',', '.')
        else:
            normalized = value.replace(',', '')
    elif ',' in value:
        normalized = value.replace('.', '').replace(',', '.')
    else:
        normalized = value

    try:
        return round(float(normalized), 2)
    except ValueError:
        return None


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword).replace(r'\ ', r'\s+')
    return re.compile(rf'(?<![{LETTER_CLASS}]){escaped}(?![{LETTER_CLASS}])', re.IGNORECASE)


def _normalize_lines(text: str) -> list[str]:
    return [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]


def _find_keyword_proximity(lines: list[str], line_idx: int, amount_pos: int) -> tuple[str | None, int | None]:
    best_keyword = None
    best_distance = None
    for offset in (-1, 0, 1):
        idx = line_idx + offset
        if idx < 0 or idx >= len(lines):
            continue
        line_lower = lines[idx].lower()
        for keyword in AMOUNT_KEYWORDS:
            pattern = _keyword_pattern(keyword)
            for match in pattern.finditer(line_lower):
                if idx == line_idx:
                    distance = abs(match.start() - amount_pos)
                else:
                    distance = 200 + abs(offset) * 25 + match.start()
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_keyword = keyword
    return best_keyword, best_distance


def _score_amount(amount: float, keyword: str | None, proximity: int | None) -> float:
    score = 0.0
    if 1 <= amount <= 1_000_000:
        score += 2.0
    else:
        score -= 5.0
    if keyword:
        score += 5.0
        if proximity is not None:
            score += max(0.0, 3.0 - min(proximity, 300) / 100.0)
    return score


def _amount_candidates(text: str) -> list[AmountCandidate]:
    lines = _normalize_lines(text)
    candidates: list[AmountCandidate] = []
    for idx, line in enumerate(lines):
        for match in AMOUNT_PATTERN.finditer(line):
            raw = match.group('amount')
            amount = parse_eur_amount(raw)
            if amount is None:
                continue
            keyword, proximity = _find_keyword_proximity(lines, idx, match.start())
            score = _score_amount(amount, keyword, proximity)
            candidates.append(AmountCandidate(amount, raw, idx, line, score, keyword, proximity))
    return candidates


def _pick_vendor(text: str, correspondent: str | None) -> VendorCandidate:
    if correspondent and str(correspondent).strip():
        return VendorCandidate(str(correspondent).strip()[:255], 'correspondent')

    lines = _normalize_lines(text)[:8]
    for line in lines:
        lower = line.lower()
        if len(line) < 3 or len(line) > 90:
            continue
        if any(_keyword_pattern(keyword).search(lower) for keyword in AMOUNT_KEYWORDS):
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


def extract_invoice_fields(text: str, correspondent: str | None) -> dict:
    text = text or ''
    vendor_candidate = _pick_vendor(text, correspondent)
    candidates = _amount_candidates(text)

    chosen: AmountCandidate | None = None
    if candidates:
        chosen = sorted(candidates, key=lambda c: (c.score, c.amount), reverse=True)[0]

    amount = chosen.amount if chosen else None
    confidence = 0.1
    if vendor_candidate.value:
        confidence += 0.35 if vendor_candidate.source == 'correspondent' else 0.2
    if chosen:
        confidence += 0.25
        if chosen.keyword:
            confidence += 0.2
        if 1 <= chosen.amount <= 1_000_000:
            confidence += 0.1
        if chosen.proximity is not None and chosen.proximity <= 30:
            confidence += 0.1
        if not (1 <= chosen.amount <= 1_000_000):
            confidence = min(confidence, 0.6)
    confidence = round(min(confidence, 0.99), 2)

    needs_review = not (vendor_candidate.value and amount is not None and confidence >= 0.65)

    context_snippet = None
    if chosen:
        all_lines = _normalize_lines(text)
        start = max(0, chosen.line_index - 1)
        end = min(len(all_lines), chosen.line_index + 2)
        context_snippet = ' | '.join(all_lines[start:end])[:500]

    debug = {
        'keyword': chosen.keyword if chosen else None,
        'regex': AMOUNT_REGEX,
        'context_snippet': context_snippet,
        'vendor_source': vendor_candidate.source,
        'candidates_checked': len(candidates),
        'extra': {
            'chosen_raw': chosen.raw if chosen else None,
            'chosen_score': chosen.score if chosen else None,
            'chosen_proximity': chosen.proximity if chosen else None,
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
