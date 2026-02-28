import json

import pytest

from api.app.extraction import extract_invoice_fields, parse_eur_amount


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('1.234,56', 1234.56),
        ('1234,56', 1234.56),
        ('1 234,56', 1234.56),
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
    assert result['needs_review'] is True  # vendor missing


def test_extract_brutto_beats_noise_summe_in_zwischensumme():
    text = '\n'.join([
        'Zwischensumme 999,99 EUR',
        'Brutto 1.050,00 EUR',
    ])
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 1050.00


def test_extract_fallback_uses_highest_plausible_amount():
    text = 'Position A 25,00\nPosition B 99,00\nPosition C 49,00'
    result = extract_invoice_fields(text, 'Fallback GmbH')
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
    text = '8rutto 1.2?4,56\nZu zahlen 124,56\nSeite 1'
    result = extract_invoice_fields(text, None)
    assert result['amount'] == 124.56


def test_out_of_range_amount_is_ignored_and_needs_review():
    text = 'Zu zahlen 12345678,99 EUR'
    result = extract_invoice_fields(text, None)
    assert result['amount'] is None
    assert result['needs_review'] is True


def test_missing_amount_sets_needs_review():
    text = 'Poolbau Muster GmbH\nRechnung ohne Betrag'
    result = extract_invoice_fields(text, None)
    assert result['amount'] is None
    assert result['needs_review'] is True


def test_debug_json_contains_expected_fields_and_top_candidates():
    result = extract_invoice_fields('Gesamt 500,00 EUR\nRabatt 20,00 EUR', 'X GmbH')
    debug = json.loads(result['debug_json'])
    assert 'regex' in debug
    assert 'context_snippet' in debug
    assert 'vendor_source' in debug
    assert 'candidates_checked' in debug
    assert 'top_candidates' in debug
    assert 'matched_keywords' in debug['top_candidates'][0]
    assert len(debug['top_candidates'][0]['line_snippet']) <= 120


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


# New extraction-specific scoring tests

def test_prefers_payable_total_over_net_and_tax():
    text = '\n'.join([
        'Netto 1.000,00 EUR',
        'MwSt 190,00 EUR',
        'Brutto 1.190,00 EUR',
        'Zahlbetrag 1.190,00 EUR',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 1190.00
    assert result['needs_review'] is False


def test_ignores_discount_line_and_selects_total():
    text = '\n'.join([
        'Rabatt -50,00 EUR',
        'Summe 450,00 EUR',
        'Zu zahlen 450,00 EUR',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 450.00


def test_ignores_skonto_amount():
    text = '\n'.join([
        'Gesamtbetrag 1.000,00 EUR',
        'Skonto bei Zahlung bis 10.01: 20,00 EUR',
        'Zu zahlen 1.000,00 EUR',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 1000.00


def test_multiple_sum_lines_prefers_endbetrag():
    text = '\n'.join([
        'Zwischensumme 780,00 EUR',
        'Summe 900,00 EUR',
        'Brutto 900,00 EUR',
        'Zu zahlen 900,00 EUR',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 900.00


def test_ocr_without_currency_symbol_still_picks_payable():
    text = '\n'.join([
        'Nettobetrag 1200,00',
        'Zu zahlen 1234,56',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 1234.56


def test_only_net_found_sets_needs_review_true():
    text = '\n'.join([
        'Nettobetrag 890,00 EUR',
        'Mehrwertsteuer 19%',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 890.00
    assert result['needs_review'] is True


def test_credit_note_negative_amount_is_not_used():
    text = '\n'.join([
        'Gutschrift',
        'Zu zahlen -120,00 EUR',
        'Rabatt -20,00 EUR',
    ])
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] is None
    assert result['needs_review'] is True


def test_negative_credit_note_debug_keeps_negative_candidates_visible():
    result = extract_invoice_fields('Gutschrift\nZu zahlen -120,00 EUR', 'ACME GmbH')
    debug = json.loads(result['debug_json'])

    assert debug['top_candidates'][0]['value'] == 120.0
    assert 'zu zahlen' in debug['top_candidates'][0]['matched_keywords']['positive']


def test_thousands_separator_with_comma_is_supported():
    text = 'Rechnungsbetrag 12.345,67 EUR'
    result = extract_invoice_fields(text, 'ACME GmbH')
    assert result['amount'] == 12345.67
