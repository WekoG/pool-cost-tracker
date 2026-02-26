import json

import pytest

from api.app.extraction import extract_invoice_fields, parse_eur_amount


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('1.234,56', 1234.56),
        ('1234,56', 1234.56),
        ('1234.56', 1234.56),
        ('12 EUR', 12.0),
    ],
)
def test_parse_eur_amount_variants(raw, expected):
    assert parse_eur_amount(raw) == expected


def test_vendor_prefers_correspondent():
    result = extract_invoice_fields('Irgendein Text\nBrutto 12,34 EUR', 'Poolbau AG')
    assert result['vendor'] == 'Poolbau AG'
    assert result['confidence'] >= 0.7


def test_extract_endbetrag_amount():
    text = 'Rechnung\nEndbetrag 2.345,67 EUR\nVielen Dank'
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 2345.67


def test_extract_zu_zahlen_beats_netto():
    text = '\n'.join([
        'Netto 1.000,00 EUR',
        'MwSt 190,00 EUR',
        'Zu zahlen 1.190,00 EUR',
    ])
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 1190.00


def test_extract_brutto_beats_noise_summe_in_zwischensumme():
    text = '\n'.join([
        'Zwischensumme 999,99 EUR',
        'Brutto 1.050,00 EUR',
    ])
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 1050.00


def test_extract_fallback_uses_highest_plausible_amount():
    text = 'Position A 25,00\nPosition B 99,00\nPosition C 49,00'
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 99.0


def test_vendor_heuristic_ignores_email_and_iban_lines():
    text = '\n'.join([
        'rechnung nr. 2026-1',
        'info@example.com',
        'IBAN DE12345678901234567890',
        'Poolservice Müller GmbH',
        'Brutto 350,00 EUR',
    ])
    result = extract_invoice_fields(text, None)
    assert result['vendor'] == 'Poolservice Müller GmbH'


def test_ocr_noise_still_extracts_amount():
    text = '8rutto 1.2?4,56\nZu zahlen 124,56 EUR\nSeite 1'
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 124.56


def test_out_of_range_amount_lowers_confidence_and_needs_review():
    text = 'Zu zahlen 12345678,99 EUR'
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 12345678.99
    assert result['needs_review'] is True
    assert result['confidence'] < 0.65


def test_missing_amount_sets_needs_review():
    text = 'Poolbau Muster GmbH\nRechnung ohne Betrag'
    result = extract_invoice_fields(text, None)
    assert result['amount'] is None
    assert result['needs_review'] is True


def test_debug_json_contains_expected_fields():
    result = extract_invoice_fields('Gesamt 500,00 EUR', 'X GmbH')
    debug = json.loads(result['debug_json'])
    assert 'regex' in debug
    assert 'context_snippet' in debug
    assert 'vendor_source' in debug
    assert 'candidates_checked' in debug


def test_confidence_higher_with_correspondent_than_without():
    text = 'Endbetrag 500,00 EUR'
    without_corr = extract_invoice_fields(text, None)
    with_corr = extract_invoice_fields(text, 'Poolbau GmbH')
    assert with_corr['confidence'] > without_corr['confidence']


def test_keyword_proximity_prefers_nearby_keyword_same_line():
    text = '\n'.join([
        'Gesamt siehe unten',
        'Artikel 100,00 EUR',
        'Bitte zu zahlen: 250,00 EUR bis morgen',
    ])
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 250.0


def test_vendor_none_when_only_artifacts_present():
    text = '\n'.join([
        'Rechnung',
        'Datum 26.02.2026',
        'Tel. 01234',
        'info@example.com',
        'IBAN DE001234',
        'Gesamt 100,00 EUR',
    ])
    result = extract_invoice_fields(text, None)
    assert result['vendor'] is None
    assert result['needs_review'] is True
