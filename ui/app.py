from __future__ import annotations

import base64
import json
import os
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

API_BASE_URL = os.getenv('API_BASE_URL', 'http://api:8000').rstrip('/')
ASSET_BG = Path(__file__).parent / 'assets' / 'pool_bg.jpg'
FONT_STACK = '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif'


@st.cache_data(ttl=5)
def api_get(path: str, params: dict | None = None):
    resp = requests.get(f'{API_BASE_URL}{path}', params=params, timeout=30)
    resp.raise_for_status()
    if path.endswith('.csv'):
        return resp.text
    return resp.json()


def api_post(path: str, payload=None):
    resp = requests.post(f'{API_BASE_URL}{path}', json=payload, timeout=120)
    _raise_with_detail(resp)
    return resp.json() if resp.content else None


def api_put(path: str, payload: dict):
    resp = requests.put(f'{API_BASE_URL}{path}', json=payload, timeout=30)
    _raise_with_detail(resp)
    return resp.json()


def api_delete(path: str):
    resp = requests.delete(f'{API_BASE_URL}{path}', timeout=30)
    _raise_with_detail(resp)
    return resp.json()


def _raise_with_detail(resp: requests.Response) -> None:
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        detail = None
        try:
            payload = resp.json()
            if isinstance(payload, dict):
                detail = payload.get('detail')
        except Exception:
            detail = None
        if detail:
            raise requests.HTTPError(f'{resp.status_code} {detail}', response=resp, request=resp.request) from exc
        raise


def clear_cache():
    api_get.clear()


def inject_theme():
    bg_css = ''
    if ASSET_BG.exists():
        encoded = base64.b64encode(ASSET_BG.read_bytes()).decode('ascii')
        bg_css = f'''
        .stApp::before {{
          content: "";
          position: fixed;
          inset: 0;
          background-image: linear-gradient(rgba(255,255,255,.86), rgba(255,255,255,.86)), url("data:image/jpeg;base64,{encoded}");
          background-size: cover;
          background-position: center;
          background-attachment: fixed;
          filter: saturate(0.95);
          z-index: -2;
        }}
        '''

    st.markdown(
        f"""
        <style>
          :root {{
            --bg: #f6f7f9;
            --card: rgba(255,255,255,0.82);
            --text: #111827;
            --muted: #6b7280;
            --border: rgba(17,24,39,0.08);
            --accent: #0a84ff;
            --shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            --radius: 18px;
          }}
          html, body, [class*="css"], .stApp {{
            font-family: {FONT_STACK};
            color: var(--text);
          }}
          .stApp {{ background: var(--bg); }}
          {bg_css}
          .block-container {{ padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }}
          .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 14px 16px;
            backdrop-filter: blur(8px);
          }}
          .kpi-grid {{ display:grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap:12px; margin: 8px 0 14px; }}
          .kpi-item {{ background: var(--card); border:1px solid var(--border); border-radius:16px; box-shadow: var(--shadow); padding: 14px; }}
          .kpi-label {{ color: var(--muted); font-size: 0.82rem; }}
          .kpi-value {{ font-weight: 650; font-size: 1.4rem; letter-spacing: -0.02em; }}
          .muted {{ color: var(--muted); }}
          div[data-testid="stMetric"] {{ background: var(--card); border:1px solid var(--border); border-radius:16px; padding:8px 10px; box-shadow: var(--shadow); }}
          div[data-testid="stDataFrame"] {{ border-radius: 16px; overflow: hidden; border: 1px solid var(--border); }}
          .stButton button, .stDownloadButton button {{ border-radius: 12px; border: 1px solid var(--border); box-shadow: var(--shadow); }}
          @media (max-width: 900px) {{ .kpi-grid {{ grid-template-columns: 1fr 1fr; }} }}
          @media (max-width: 560px) {{ .kpi-grid {{ grid-template-columns: 1fr; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def fmt_eur(value):
    if value is None:
        return '-'
    return f'{float(value):,.2f} EUR'.replace(',', 'X').replace('.', ',').replace('X', '.')


def section_card(title: str, subtitle: str | None = None):
    subtitle_html = f'<div class="muted">{subtitle}</div>' if subtitle else ''
    st.markdown(f'<div class="card"><h3 style="margin:0 0 4px 0;">{title}</h3>{subtitle_html}</div>', unsafe_allow_html=True)


def dashboard_page():
    st.title('Dashboard')
    cfg = api_get('/config')
    summary = api_get('/summary')

    col_sync, col_info = st.columns([1, 2])
    with col_sync:
        if st.button('Sync jetzt', use_container_width=True, type='primary'):
            try:
                with st.spinner('Synchronisierung läuft...'):
                    result = api_post('/sync')
                clear_cache()
                st.success(f"{result['synced']} Dokumente synchronisiert ({result['inserted']} neu, {result['updated']} aktualisiert)")
                summary = api_get('/summary')
                cfg = api_get('/config')
            except requests.HTTPError as exc:
                st.error(f'Sync fehlgeschlagen: {exc}')
    with col_info:
        st.markdown(
            f"<div class='card'><div><b>Scheduler</b>: {'aktiv' if cfg['scheduler_enabled'] else 'inaktiv'}</div>"
            f"<div class='muted'>Intervall: {cfg['scheduler_interval_minutes']} min | Run on startup: {cfg['scheduler_run_on_startup']}</div>"
            f"<div class='muted'>Paperless Base URL: {cfg['paperless_base_url']}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-item"><div class="kpi-label">Gesamtsumme</div><div class="kpi-value">{fmt_eur(summary['total_amount'])}</div></div>
          <div class="kpi-item"><div class="kpi-label">Paperless</div><div class="kpi-value">{fmt_eur(summary['paperless_total'])}</div></div>
          <div class="kpi-item"><div class="kpi-label">Manuell</div><div class="kpi-value">{fmt_eur(summary['manual_total'])}</div></div>
          <div class="kpi-item"><div class="kpi-label">Needs Review</div><div class="kpi-value">{summary['needs_review_count']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        section_card('Top 10 Vendors', 'Summierte Paperless-Kosten nach Lieferant')
        top_df = pd.DataFrame(summary.get('top_vendors', []))
        if top_df.empty:
            st.info('Noch keine Rechnungen vorhanden.')
        else:
            top_df = top_df.rename(columns={'name': 'Vendor', 'amount': 'Betrag'})
            st.dataframe(top_df, use_container_width=True, hide_index=True)
            st.bar_chart(top_df.set_index('Vendor')['Betrag'])
    with right:
        section_card('Kosten nach Kategorie', 'Nur manuelle Kostenpositionen')
        cat_df = pd.DataFrame(summary.get('costs_by_category', []))
        if cat_df.empty:
            st.info('Noch keine manuellen Kategorien vorhanden.')
        else:
            cat_df = cat_df.rename(columns={'category': 'Kategorie', 'amount': 'Betrag'})
            st.dataframe(cat_df, use_container_width=True, hide_index=True)
            st.bar_chart(cat_df.set_index('Kategorie')['Betrag'])


def invoices_page():
    st.title('Paperless-Rechnungen')
    f1, f2, f3 = st.columns([1, 2, 1])
    with f1:
        needs_review_filter = st.selectbox('Needs Review', ['Alle', 'Ja', 'Nein'])
    with f2:
        search = st.text_input('Vendor/Titel suchen', placeholder='z. B. Poolbau')
    with f3:
        sort = st.selectbox('Sortierung', ['date_desc', 'amount_desc', 'vendor_asc'])

    params = {'sort': sort}
    if needs_review_filter == 'Ja':
        params['needs_review'] = 'true'
    elif needs_review_filter == 'Nein':
        params['needs_review'] = 'false'
    if search.strip():
        params['search'] = search.strip()

    invoices = api_get('/invoices', params=params)
    if not invoices:
        st.info('Keine Rechnungen gefunden.')
        return

    df = pd.DataFrame(invoices)
    display_cols = [c for c in ['id', 'paperless_doc_id', 'paperless_created', 'vendor', 'amount', 'currency', 'confidence', 'needs_review', 'title'] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

    st.subheader('Rechnung prüfen / korrigieren')
    options = {f"#{row['id']} | {row.get('vendor') or '-'} | {row.get('title') or '-'}": row for row in invoices}
    selected_label = st.selectbox('Auswahl', list(options.keys()))
    selected = options[selected_label]

    snippet = selected.get('ocr_snippet') or ''
    debug_json = selected.get('debug_json')
    if debug_json:
        try:
            dbg = json.loads(debug_json)
            snippet = dbg.get('context_snippet') or snippet
        except json.JSONDecodeError:
            pass

    with st.form('invoice_edit_form'):
        vendor = st.text_input('Vendor', value=selected.get('vendor') or '')
        amount = st.number_input('Betrag (EUR)', min_value=0.0, step=0.01, value=float(selected.get('amount') or 0.0))
        needs_review = st.checkbox('Needs Review', value=bool(selected.get('needs_review', True)))
        st.text_area('OCR Kontextsnippet', value=snippet, height=120, disabled=True)
        save = st.form_submit_button('Speichern')
    if save:
        api_put(f"/invoices/{selected['id']}", {'vendor': vendor or None, 'amount': float(amount), 'needs_review': needs_review})
        clear_cache()
        st.success('Rechnung aktualisiert.')


def manual_costs_page():
    st.title('Manuelle Kosten')
    st.subheader('Neue Position')
    with st.form('manual_create'):
        c1, c2 = st.columns(2)
        with c1:
            m_date = st.date_input('Datum')
            vendor = st.text_input('Vendor')
            amount = st.number_input('Betrag (EUR)', min_value=0.01, step=0.01)
        with c2:
            category = st.text_input('Kategorie')
            note = st.text_area('Notiz', height=110)
        submit = st.form_submit_button('Anlegen')
    if submit:
        api_post('/manual-costs', {
            'date': m_date.isoformat(),
            'vendor': vendor,
            'amount': float(amount),
            'category': category or None,
            'note': note or None,
            'currency': 'EUR',
        })
        clear_cache()
        st.success('Manuelle Kostenposition angelegt.')

    rows = api_get('/manual-costs')
    if not rows:
        st.info('Noch keine manuellen Kosten vorhanden.')
        return

    df = pd.DataFrame(rows)
    st.dataframe(df[['id', 'date', 'vendor', 'amount', 'currency', 'category', 'note']], use_container_width=True, hide_index=True)

    st.subheader('Bearbeiten / Löschen')
    options = {f"#{r['id']} | {r['vendor']} | {r['amount']} {r['currency']}": r for r in rows}
    selected_label = st.selectbox('Eintrag', list(options.keys()))
    selected = options[selected_label]
    with st.form('manual_edit'):
        e_date = st.date_input('Datum', value=pd.to_datetime(selected['date']).date())
        e_vendor = st.text_input('Vendor', value=selected['vendor'])
        e_amount = st.number_input('Betrag (EUR)', min_value=0.01, step=0.01, value=float(selected['amount']))
        e_category = st.text_input('Kategorie', value=selected.get('category') or '')
        e_note = st.text_area('Notiz', value=selected.get('note') or '', height=100)
        col_a, col_b = st.columns(2)
        save = col_a.form_submit_button('Speichern')
        delete = col_b.form_submit_button('Löschen')
    if save:
        api_put(f"/manual-costs/{selected['id']}", {
            'date': e_date.isoformat(),
            'vendor': e_vendor,
            'amount': float(e_amount),
            'category': e_category or None,
            'note': e_note or None,
            'currency': selected.get('currency', 'EUR'),
        })
        clear_cache()
        st.success('Eintrag aktualisiert.')
    if delete:
        api_delete(f"/manual-costs/{selected['id']}")
        clear_cache()
        st.success('Eintrag gelöscht.')


def export_page():
    st.title('Export')
    csv_text = api_get('/export.csv')
    st.download_button('CSV herunterladen', data=csv_text.encode('utf-8'), file_name='pool_costs_export.csv', mime='text/csv', use_container_width=True)
    if csv_text.strip():
        df = pd.read_csv(StringIO(csv_text))
        st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title='pool-cost-tracker', layout='wide')
    inject_theme()
    st.sidebar.markdown('## pool-cost-tracker')
    st.sidebar.caption(f'API: {API_BASE_URL}')
    page = st.sidebar.radio('Seiten', ['Dashboard', 'Paperless-Rechnungen', 'Manuelle Kosten', 'Export'])

    try:
        if page == 'Dashboard':
            dashboard_page()
        elif page == 'Paperless-Rechnungen':
            invoices_page()
        elif page == 'Manuelle Kosten':
            manual_costs_page()
        else:
            export_page()
    except requests.RequestException as exc:
        st.error(f'API-Fehler: {exc}')


if __name__ == '__main__':
    main()
