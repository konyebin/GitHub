"""ASE Candidate Tracker: a local Streamlit UI for the FY27Q3 AMER ASE scores workbook.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import hashlib
import html
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tracker_core import (
    ALL_STATUSES,
    CISCO_BLUE,
    DEFAULT_HIRE_THRESHOLD,
    DEFAULT_STANDBY_THRESHOLD,
    HIRE,
    NO_HIRE,
    SECTIONS,
    STANDBY,
    UI_COLORS,
    UNASSIGNED,
    build_workbook,
    duplicate_numbers,
    parse_workbook,
    suggest,
)

APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "tracker_state.json"
SECTION_LABELS = list(SECTIONS.values())

st.set_page_config(page_title="ASE Candidate Tracker", layout="wide", page_icon=":bar_chart:")

CSS = f"""
<style>
  #MainMenu, footer {{ visibility: hidden; }}
  .block-container {{ padding-top: 3.2rem; max-width: 1500px; }}
  .hero {{
    background: linear-gradient(120deg, #0E2238 0%, #0A1220 55%, #0B2F47 100%);
    border: 1px solid #16324C; border-radius: 16px; padding: 22px 28px; margin-bottom: 18px;
    position: relative; overflow: hidden;
  }}
  .hero::after {{
    content: ""; position: absolute; right: -60px; top: -60px; width: 220px; height: 220px;
    border-radius: 50%; background: radial-gradient(circle, {CISCO_BLUE}55, transparent 70%);
  }}
  .hero h1 {{ margin: 0; font-size: 1.9rem; letter-spacing: .2px; }}
  .hero h1 span {{ color: {CISCO_BLUE}; }}
  .hero p {{ margin: 4px 0 0 0; color: #9FB3C8; font-size: .95rem; }}
  .kpi {{
    background: #111C2E; border: 1px solid #1C2B42; border-radius: 14px; padding: 14px 18px;
    border-left: 5px solid var(--c); height: 100%;
  }}
  .kpi .n {{ font-size: 2rem; font-weight: 700; line-height: 1.1; color: var(--c); }}
  .kpi .l {{ color: #9FB3C8; font-size: .8rem; text-transform: uppercase; letter-spacing: 1px; }}
  .colhead {{
    border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; font-weight: 700;
    display: flex; justify-content: space-between; align-items: center;
    background: color-mix(in srgb, var(--c) 18%, #0A1220); color: var(--c);
    border: 1px solid color-mix(in srgb, var(--c) 45%, #0A1220);
  }}
  .colhead .count {{ background: var(--c); color: #0A1220; border-radius: 999px; padding: 1px 10px; font-size: .85rem; }}
  .card-name {{ font-weight: 650; font-size: 1rem; }}
  .card-meta {{ color: #9FB3C8; font-size: .78rem; margin-top: 2px; }}
  .bar {{ height: 6px; border-radius: 6px; background: #1C2B42; margin: 8px 0 2px 0; overflow: hidden; }}
  .bar > div {{ height: 100%; background: var(--c); }}
  .pill {{
    display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: .72rem; font-weight: 600;
    background: color-mix(in srgb, var(--c) 20%, #0A1220); color: var(--c);
    border: 1px solid color-mix(in srgb, var(--c) 50%, #0A1220); margin-right: 4px;
  }}
  div[data-testid="stTabs"] button[role="tab"] {{ font-size: 1.02rem; padding: 10px 18px; }}
  div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 12px; }}
  .stButton > button, .stDownloadButton > button {{ border-radius: 10px; }}
  div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {{
    padding: .15rem .1rem; font-size: .74rem; min-height: 2rem; white-space: nowrap;
  }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_iso(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NaT:
        return ""
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


# ---------------------------------------------------------------- state ---

def load_state_file() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def persist() -> None:
    payload = {
        "decisions": st.session_state.decisions,
        "audit": st.session_state.audit,
        "reviewer": st.session_state.get("reviewer", ""),
        "hire_th": st.session_state.get("hire_th", DEFAULT_HIRE_THRESHOLD),
        "standby_th": st.session_state.get("standby_th", DEFAULT_STANDBY_THRESHOLD),
    }
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    os.replace(tmp, STATE_FILE)


def init_state() -> None:
    if "decisions" in st.session_state:
        return
    saved = load_state_file()
    st.session_state.decisions = saved.get("decisions", {})
    st.session_state.audit = saved.get("audit", [])
    st.session_state.reviewer = saved.get("reviewer", "")
    st.session_state.hire_th = saved.get("hire_th", DEFAULT_HIRE_THRESHOLD)
    st.session_state.standby_th = saved.get("standby_th", DEFAULT_STANDBY_THRESHOLD)
    st.session_state.rev = 0
    st.session_state.search = ""


def decision(name: str) -> dict[str, str]:
    return st.session_state.decisions.get(name, {})


def source_status(name: str) -> str:
    return st.session_state.source_status.get(name, UNASSIGNED)


def current_status(name: str) -> str:
    return decision(name).get("status", source_status(name))


def set_field(name: str, field: str, value: str, label: str, commit: bool = True) -> bool:
    """Update one decision field, write an audit entry and report whether it changed."""
    record = st.session_state.decisions.setdefault(name, {})
    default = source_status(name) if field == "status" else ""
    old = record.get(field, default)
    if old == value:
        return False
    record[field] = value
    st.session_state.audit.append(
        {
            "when": now_text(),
            "by": st.session_state.reviewer or "-",
            "candidate": name,
            "field": label,
            "old": old or "-",
            "new": value or "-",
        }
    )
    st.session_state.rev += 1
    if commit:
        persist()
    return True


def merged_frame(base: pd.DataFrame) -> pd.DataFrame:
    df = base.copy()
    df["Status"] = [current_status(n) for n in df["Candidate"]]
    df["Employee #"] = [decision(n).get("emp_no", "") for n in df["Candidate"]]
    df["Re-evaluate On"] = [
        date.fromisoformat(d) if (d := decision(n).get("reeval", "")) else None
        for n in df["Candidate"]
    ]
    df["Decision Notes"] = [decision(n).get("notes", "") for n in df["Candidate"]]
    df["Suggested"] = [
        suggest(p, c, st.session_state.hire_th, st.session_state.standby_th)
        for p, c in zip(df["Overall %"], df["Complete"])
    ]
    return df


# -------------------------------------------------------------- widgets ---

def kpi(label: str, value: int, color: str) -> str:
    return f'<div class="kpi" style="--c:{color}"><div class="n">{value}</div><div class="l">{label}</div></div>'


def row_style(row: pd.Series) -> list[str]:
    color = UI_COLORS[row["Status"]]
    alpha = "30" if row["Status"] != UNASSIGNED else "14"
    css = f"background-color: {color}{alpha};"
    if row["Status"] != UNASSIGNED:
        css += f" color: {color};"
    return [css] * len(row)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df
    query = st.session_state.search.strip().lower()
    if query:
        out = out[
            out["Candidate"].str.lower().str.contains(query, regex=False)
            | out["Country"].str.lower().str.contains(query, regex=False)
            | out["Employee #"].str.lower().str.contains(query, regex=False)
        ]
    return out


def tab_all(df: pd.DataFrame) -> None:
    st.caption(
        "Rows are coloured by status: green is Hire, yellow is Standby, red is No Hire. "
        "Change a status, re-evaluation date or note straight in the table."
    )
    c1, c2 = st.columns([3, 1])
    with c1:
        picked = st.multiselect("Show statuses", ALL_STATUSES, default=ALL_STATUSES, key="all_filter")
    with c2:
        sort = st.selectbox("Sort by", ["Score (high to low)", "Name (A-Z)", "Status"], key="all_sort")
    view = apply_filters(df)
    view = view[view["Status"].isin(picked)]
    if sort.startswith("Score"):
        view = view.sort_values("Overall %", ascending=False)
    elif sort.startswith("Name"):
        view = view.sort_values("Candidate")
    else:
        view = view.sort_values(
            "Status", key=lambda s: s.map({x: i for i, x in enumerate([HIRE, STANDBY, NO_HIRE, UNASSIGNED])})
        )
    columns = [
        "Candidate", "Country", "Interview", "Role Play", "Presentation", "Total",
        "Overall %", "Status", "Re-evaluate On", "Decision Notes",
    ]
    view = view[columns].reset_index(drop=True)
    if view.empty:
        st.info("No candidates match the current filters.")
        return

    styled = view.style.apply(row_style, axis=1)
    edited = st.data_editor(
        styled,
        hide_index=True,
        width="stretch",
        height=min(640, 60 + 36 * len(view)),
        key=f"all_editor_{st.session_state.rev}",
        disabled=["Candidate", "Country", "Interview", "Role Play", "Presentation", "Total", "Overall %"],
        column_config={
            "Interview": st.column_config.NumberColumn("Interview /16", format="%.1f"),
            "Role Play": st.column_config.NumberColumn("Role Play /16", format="%.1f"),
            "Presentation": st.column_config.NumberColumn("Presentation /16", format="%.1f"),
            "Total": st.column_config.NumberColumn("Total /48", format="%.1f"),
            "Overall %": st.column_config.ProgressColumn("Overall", min_value=0.0, max_value=1.0, format="percent"),
            "Status": st.column_config.SelectboxColumn("Status", options=ALL_STATUSES, required=True),
            "Re-evaluate On": st.column_config.DateColumn("Re-evaluate on", format="YYYY-MM-DD"),
            "Decision Notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )
    changed = False
    for row in edited.to_dict("records"):
        name = row["Candidate"]
        changed |= set_field(name, "status", row["Status"], "Status", commit=False)
        changed |= set_field(name, "reeval", to_iso(row["Re-evaluate On"]), "Re-evaluate on", commit=False)
        changed |= set_field(name, "notes", clean_text(row["Decision Notes"]), "Notes", commit=False)
    if changed:
        persist()
        st.rerun()


def card(row: pd.Series, status: str) -> None:
    color = UI_COLORS[status]
    pct = row["Overall %"]
    badges = ""
    if row["Employee #"] and status == HIRE:
        badges += f'<span class="pill" style="--c:{CISCO_BLUE}">#{html.escape(row["Employee #"])}</span>'
    if status == UNASSIGNED and row["Suggested"] != "Incomplete":
        badges += f'<span class="pill" style="--c:{UI_COLORS[row["Suggested"]]}">suggests {row["Suggested"]}</span>'
    if status == STANDBY and row["Re-evaluate On"]:
        badges += f'<span class="pill" style="--c:{UI_COLORS[STANDBY]}">re-eval {row["Re-evaluate On"]:%b %d}</span>'
    meta = html.escape(row["Country"]) if row["Country"] else "&nbsp;"
    with st.container(border=True):
        st.markdown(
            f'<div style="--c:{color}">'
            f'<div class="card-name">{html.escape(row["Candidate"])}</div>'
            f'<div class="card-meta">{meta} &middot; {row["Total"]:.1f}/48 &middot; {pct:.0%}</div>'
            f'<div class="bar"><div style="width:{min(pct, 1) * 100:.0f}%"></div></div>'
            f"<div>{badges}</div></div>",
            unsafe_allow_html=True,
        )
        options = [HIRE, STANDBY, NO_HIRE, UNASSIGNED]
        for pair in (options[:2], options[2:]):
            for col, target in zip(st.columns(2), pair):
                label = "Unassign" if target == UNASSIGNED else target
                is_current = target == status
                if col.button(
                    label,
                    key=f"mv_{row['Candidate']}_{target}",
                    width="stretch",
                    type="primary" if is_current else "secondary",
                    disabled=is_current,
                ):
                    set_field(row["Candidate"], "status", target, "Status")
                    st.rerun()


def tab_board(df: pd.DataFrame) -> None:
    st.caption("Each candidate sits in the column for their status. Use the buttons on a card to move them.")
    view = apply_filters(df).sort_values("Overall %", ascending=False)
    order = [UNASSIGNED, HIRE, STANDBY, NO_HIRE]
    cols = st.columns(len(order))
    for col, status in zip(cols, order):
        subset = view[view["Status"] == status]
        with col:
            st.markdown(
                f'<div class="colhead" style="--c:{UI_COLORS[status]}"><span>{status}</span>'
                f'<span class="count">{len(subset)}</span></div>',
                unsafe_allow_html=True,
            )
            if subset.empty:
                st.caption("Nobody here yet.")
            for _, row in subset.iterrows():
                card(row, status)


def tab_employee_numbers(df: pd.DataFrame) -> None:
    hires = df[df["Status"] == HIRE]
    numbers = dict(zip(df["Candidate"], df["Employee #"]))
    dupes = duplicate_numbers(numbers)
    have = int((hires["Employee #"].str.strip() != "").sum())
    m1, m2, m3 = st.columns(3)
    m1.markdown(kpi("Hires", len(hires), UI_COLORS[HIRE]), unsafe_allow_html=True)
    m2.markdown(kpi("Numbers assigned", have, CISCO_BLUE), unsafe_allow_html=True)
    m3.markdown(kpi("Still needed", len(hires) - have, UI_COLORS[STANDBY]), unsafe_allow_html=True)
    st.write("")

    for number, who in dupes.items():
        shown = next((numbers[w] for w in who), number)
        st.warning(f"Employee number **{shown}** is used by more than one candidate: {', '.join(who)}.")

    if hires.empty:
        st.info("Mark candidates as Hire on the first two tabs, then add their employee numbers here.")
    else:
        dup_names = {w for who in dupes.values() for w in who}
        table = hires.sort_values("Candidate")[["Candidate", "Country", "Overall %", "Employee #"]].copy()
        table["Check"] = [
            "Duplicate" if c in dup_names else ("Needed" if not n.strip() else "OK")
            for c, n in zip(table["Candidate"], table["Employee #"])
        ]
        table = table.reset_index(drop=True)

        def check_style(row: pd.Series) -> list[str]:
            color = {"OK": UI_COLORS[HIRE], "Needed": UI_COLORS[STANDBY], "Duplicate": UI_COLORS[NO_HIRE]}[row["Check"]]
            return [f"background-color: {UI_COLORS[HIRE]}22;"] * 3 + [f"background-color: {color}33; color: {color};"] * 2

        edited = st.data_editor(
            table.style.apply(check_style, axis=1),
            hide_index=True,
            width="stretch",
            key=f"emp_editor_{st.session_state.rev}",
            disabled=["Candidate", "Country", "Overall %", "Check"],
            column_config={
                "Overall %": st.column_config.ProgressColumn("Overall", min_value=0.0, max_value=1.0, format="percent"),
                "Employee #": st.column_config.TextColumn("Employee #", help="Type or paste the employee number"),
            },
        )
        changed = False
        for row in edited.to_dict("records"):
            changed |= set_field(row["Candidate"], "emp_no", clean_text(row["Employee #"]), "Employee #", commit=False)
        if changed:
            persist()
            st.rerun()

    kept = df[(df["Status"] != HIRE) & (df["Employee #"].str.strip() != "")]
    if not kept.empty:
        with st.expander(f"Numbers kept for candidates no longer on Hire ({len(kept)})"):
            st.caption("These numbers are retained and come back automatically if the candidate is moved to Hire again.")
            st.dataframe(
                kept[["Candidate", "Status", "Employee #"]].reset_index(drop=True),
                hide_index=True,
                width="stretch",
            )


def plotly_dark(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E8EEF7"),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=-0.3),
    )
    return fig


def tab_insights(df: pd.DataFrame) -> None:
    c1, c2 = st.columns(2)
    counts = df["Status"].value_counts()
    donut = go.Figure(
        go.Pie(
            labels=ALL_STATUSES,
            values=[int(counts.get(s, 0)) for s in ALL_STATUSES],
            hole=0.62,
            marker=dict(colors=[UI_COLORS[s] for s in ALL_STATUSES], line=dict(color="#0A1220", width=3)),
            sort=False,
        )
    )
    donut.update_layout(title="Decision split", annotations=[dict(text=f"{len(df)}<br>candidates", showarrow=False, font=dict(size=16))])
    c1.plotly_chart(plotly_dark(donut), width="stretch")

    hist = go.Figure()
    for status in ALL_STATUSES:
        subset = df[df["Status"] == status]
        if len(subset):
            hist.add_trace(go.Histogram(x=subset["Overall %"] * 100, name=status, marker_color=UI_COLORS[status], xbins=dict(size=5)))
    hist.update_layout(barmode="stack", title="Score distribution (overall %)", xaxis_title="Overall %", yaxis_title="Candidates")
    hist.add_vline(x=st.session_state.hire_th * 100, line_dash="dash", line_color=UI_COLORS[HIRE])
    hist.add_vline(x=st.session_state.standby_th * 100, line_dash="dash", line_color=UI_COLORS[STANDBY])
    c2.plotly_chart(plotly_dark(hist), width="stretch")

    c3, c4 = st.columns(2)
    avg = go.Figure()
    for status in [HIRE, STANDBY, NO_HIRE]:
        subset = df[df["Status"] == status]
        if len(subset):
            avg.add_trace(
                go.Bar(
                    x=SECTION_LABELS,
                    y=[subset[s].mean() for s in SECTION_LABELS],
                    name=status,
                    marker_color=UI_COLORS[status],
                )
            )
    avg.update_layout(barmode="group", title="Average section score by status (max 16)", yaxis=dict(range=[0, 16]))
    c3.plotly_chart(plotly_dark(avg), width="stretch")

    with c4:
        st.markdown("**Standby re-evaluation queue**")
        standby = df[(df["Status"] == STANDBY)].copy()
        if standby.empty:
            st.caption("No one on standby.")
        else:
            today = date.today()
            standby["Due"] = standby["Re-evaluate On"].apply(
                lambda d: "No date set" if d is None else ("Overdue" if d < today else f"In {(d - today).days} days")
            )
            standby = standby.sort_values("Re-evaluate On", na_position="last")
            st.dataframe(
                standby[["Candidate", "Overall %", "Re-evaluate On", "Due", "Decision Notes"]].reset_index(drop=True),
                hide_index=True,
                width="stretch",
                column_config={"Overall %": st.column_config.ProgressColumn("Overall", min_value=0.0, max_value=1.0, format="percent")},
            )

    st.markdown("**Audit log**")
    audit = pd.DataFrame(st.session_state.audit[::-1], columns=["when", "by", "candidate", "field", "old", "new"])
    if audit.empty:
        st.caption("Changes you make will be listed here with a timestamp and your reviewer name.")
    else:
        st.dataframe(audit, hide_index=True, width="stretch")


# ----------------------------------------------------------------- main ---

init_state()

with st.sidebar:
    st.markdown("### Workbook")
    upload = st.file_uploader("Upload the ASE scores workbook", type=["xlsx"], label_visibility="collapsed")
    include_examples = st.toggle("Include 'Example' rows", value=False)
    st.text_input("Reviewer name", key="reviewer", on_change=persist, help="Stamped on every change in the audit log.")
    st.markdown("### Suggestion thresholds")
    st.slider("Suggest Hire at or above", 0.5, 1.0, key="hire_th", step=0.01, format="%.2f", on_change=persist)
    st.slider("Suggest Standby at or above", 0.3, 1.0, key="standby_th", step=0.01, format="%.2f", on_change=persist)

st.markdown(
    '<div class="hero"><h1>ASE Candidate <span>Tracker</span></h1>'
    "<p>FY27Q3 AMER &middot; Hire, standby and no-hire decisions with employee numbers</p></div>",
    unsafe_allow_html=True,
)

if upload is None:
    st.info("Upload the **FY27Q3_AMER_ASE_Scores** workbook in the sidebar to begin.")
    st.stop()

raw = upload.getvalue()
digest = hashlib.sha1(raw).hexdigest() + str(include_examples)
if st.session_state.get("digest") != digest:
    try:
        parsed = parse_workbook(raw, include_examples=include_examples)
    except Exception as exc:  # surface parse problems to the user
        st.error(f"Could not read that workbook: {exc}")
        st.stop()
    st.session_state.base = parsed.df
    st.session_state.source_status = dict(zip(parsed.df["Candidate"], parsed.df["Source Status"]))
    st.session_state.skipped = parsed.skipped_examples
    st.session_state.digest = digest

base: pd.DataFrame = st.session_state.base
if base.empty:
    st.warning("No candidates found yet. Fill in candidate names in the workbook and upload it again.")
    st.stop()

df = merged_frame(base)
suffix = "_tracked"
stem = Path(upload.name).stem
stem = stem[: -len(suffix)] if stem.endswith(suffix) else stem
output_path = APP_DIR / f"{stem}{suffix}.xlsx"

with st.sidebar:
    st.markdown("### Actions")
    unassigned_ready = df[(df["Status"] == UNASSIGNED) & df["Suggested"].isin([HIRE, STANDBY, NO_HIRE])]
    if st.button(f"Apply suggestions to {len(unassigned_ready)} unassigned", disabled=unassigned_ready.empty, width="stretch"):
        for name, suggestion in zip(unassigned_ready["Candidate"], unassigned_ready["Suggested"]):
            set_field(name, "status", suggestion, "Status (suggestion applied)", commit=False)
        persist()
        st.rerun()
    workbook_bytes = build_workbook(df, st.session_state.audit, st.session_state.hire_th, st.session_state.standby_th)
    if st.button("Save to Excel", type="primary", width="stretch"):
        output_path.write_bytes(workbook_bytes)
        st.session_state.saved_msg = f"Saved {output_path.name} next to app.py at {now_text()}"
    if st.session_state.get("saved_msg"):
        st.success(st.session_state.saved_msg)
    st.download_button(
        "Download .xlsx",
        workbook_bytes,
        file_name=output_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    if st.session_state.skipped and not include_examples:
        st.caption(f"{st.session_state.skipped} example row(s) hidden.")
    with st.expander("Reset all decisions"):
        st.caption("Clears your changes (statuses go back to what the workbook says), employee numbers, notes and the audit log.")
        if st.button("Reset everything", width="stretch"):
            st.session_state.decisions = {}
            st.session_state.audit = []
            st.session_state.rev += 1
            persist()
            st.rerun()

counts = df["Status"].value_counts()
kpi_cols = st.columns(5)
kpi_data = [("Candidates", len(df), CISCO_BLUE)] + [(s, int(counts.get(s, 0)), UI_COLORS[s]) for s in [HIRE, STANDBY, NO_HIRE, UNASSIGNED]]
for col, (label, value, color) in zip(kpi_cols, kpi_data):
    col.markdown(kpi(label, value, color), unsafe_allow_html=True)
decided = len(df) - int(counts.get(UNASSIGNED, 0))
st.progress(decided / len(df), text=f"{decided} of {len(df)} candidates decided")

st.text_input("Search by name, country or employee number", key="search", placeholder="Start typing...")

t1, t2, t3, t4 = st.tabs(["All Candidates", "Board", "Employee Numbers", "Insights & Log"])
with t1:
    tab_all(df)
with t2:
    tab_board(df)
with t3:
    tab_employee_numbers(df)
with t4:
    tab_insights(df)
