#!/usr/bin/env python3
"""Generate hackathon demo ops reports from synthetic Webex-style CSVs."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "ops-report-source.html"

REPORT_TYPES = {
    "cdr": "Calling Detailed Call History",
    "call_queue": "Call Queue Stats",
    "aa_summary": "Auto-Attendant Stats Summary",
    "media_quality": "Calling Media Quality Report",
    "connectivity": "Calling Connectivity",
}


@dataclass
class Scenario:
    slug: str
    title: str
    org_name: str
    tagline: str
    seed: int
    cdr_legs: int
    aa_answer_bias: float  # 0-1 target AA answer rate
    queue_abandon_bias: float  # 0-1 target abandon share
    intl_share: float
    poor_mq_share: float
    disconnected_devices: int
    rec_fail_rate: float


SCENARIOS = [
    Scenario(
        slug="healthy-campus",
        title="Healthy Campus",
        org_name="Northwind University",
        tagline="Well-run enterprise — mostly green scorecard, high volume",
        seed=42,
        cdr_legs=920,
        aa_answer_bias=0.94,
        queue_abandon_bias=0.04,
        intl_share=0.06,
        poor_mq_share=0.02,
        disconnected_devices=0,
        rec_fail_rate=0.0,
    ),
    Scenario(
        slug="contact-center-pressure",
        title="Contact Center Under Pressure",
        org_name="Acme Retail Group",
        tagline="High queue abandonment, staffing gaps, mixed scorecard",
        seed=7,
        cdr_legs=1180,
        aa_answer_bias=0.64,
        queue_abandon_bias=0.42,
        intl_share=0.08,
        poor_mq_share=0.06,
        disconnected_devices=2,
        rec_fail_rate=0.004,
    ),
    Scenario(
        slug="global-expansion",
        title="Global Expansion",
        org_name="Horizon Logistics",
        tagline="International growth pains — routing, PSTN, and recording signals",
        seed=99,
        cdr_legs=1050,
        aa_answer_bias=0.81,
        queue_abandon_bias=0.18,
        intl_share=0.22,
        poor_mq_share=0.09,
        disconnected_devices=5,
        rec_fail_rate=0.012,
    ),
]

LOCATIONS = ["Chicago", "Dallas", "Denver", "London", "Singapore"]
AGENTS = [
    "Alex Morgan", "Jordan Lee", "Sam Chen", "Taylor Brooks", "Casey Rivera",
    "Morgan Quinn", "Riley Park", "Jamie Ortiz", "Priya Nair", "Marcus Webb",
]
AA_NAMES = [
    "Main Reception AA", "After Hours AA", "Sales IVR", "Support IVR",
    "Billing AA", "HR Hotline AA", "Facilities AA", "Executive AA",
]
QUEUE_NAMES = [
    "Sales Queue East", "Support Queue East", "Billing Queue",
    "VIP Queue", "Overflow Queue", "Technical Triage", "Returns Desk",
]
CALL_TYPES = [
    ("SIP_ENTERPRISE", 0.55, "Internal — no PSTN cost"),
    ("SIP_INBOUND", 0.18, "Inbound PSTN"),
    ("SIP_NATIONAL", 0.12, "Outbound national"),
    ("SIP_MOBILE", 0.08, "Outbound mobile"),
    ("SIP_INTERNATIONAL", 0.05, "Outbound international"),
    ("UNKNOWN", 0.01, "Unrecognized route"),
    ("SIP_SHORTCODE", 0.01, "911 / freephone"),
]
OUTCOME_REASONS = ["CallRejected", "TemporarilyUnavailable", "UnassignedNumber", "Success"]


def period() -> tuple[str, str, str]:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=30)
    label = f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"
    return start.isoformat(), end.isoformat(), label


def pill(status: str) -> str:
    labels = {"good": "Good", "warn": "Needs Attention", "bad": "Action Required"}
    return f'<span class="pill {status}">{labels[status]}</span>'


def badge(status: str) -> str:
    icons = {"good": "🟢 Good", "warn": "🟡 Needs Attention", "bad": "🔴 Action Required"}
    return icons[status]


def pct_status(val: float, good: float, warn: float, high_is_good: bool = False) -> str:
    if high_is_good:
        if val >= good:
            return "good"
        if val >= warn:
            return "warn"
        return "bad"
    if val <= good:
        return "good"
    if val <= warn:
        return "warn"
    return "bad"


def weighted_choice(rng: random.Random, items: list[tuple]) -> str:
    total = sum(w for _, w, _ in items)
    pick = rng.uniform(0, total)
    acc = 0.0
    for name, w, _ in items:
        acc += w
        if pick <= acc:
            return name
    return items[-1][0]


def generate_aa_summary(rng: random.Random, sc: Scenario) -> pd.DataFrame:
    rows = []
    for name in AA_NAMES:
        loc = rng.choice(LOCATIONS)
        total = rng.randint(8, 120)
        answered = int(total * rng.uniform(sc.aa_answer_bias - 0.08, sc.aa_answer_bias + 0.05))
        answered = max(0, min(total, answered))
        rows.append({
            "Auto Attendant": name,
            "Ph.No./Extn.": f"+1{rng.randint(200,999)}{rng.randint(2000000,9999999)}",
            "Location": loc,
            "Total Calls": total,
            "Answered": answered,
            "Unanswered": total - answered,
            "Busy": rng.randint(0, max(0, total // 10)),
            "Others": 0,
            "% Answered": round(answered / total * 100, 1) if total else 0,
            "Total Duration": rng.randint(200, 8000),
            "Total AA Talktime": rng.randint(100, 4000),
        })
    return pd.DataFrame(rows)


def generate_call_queue(rng: random.Random, sc: Scenario) -> pd.DataFrame:
    rows = []
    for name in QUEUE_NAMES:
        loc = rng.choice(LOCATIONS)
        total = rng.randint(40, 280)
        abandon_pct = rng.uniform(sc.queue_abandon_bias - 0.12, sc.queue_abandon_bias + 0.15)
        abandon_pct = max(0.02, min(0.75, abandon_pct))
        abandoned = int(total * abandon_pct)
        answered = total - abandoned
        rows.append({
            "Call Queue": name,
            "Location": loc,
            "Phone NO.": f"+1{rng.randint(200,999)}{rng.randint(2000000,9999999)}",
            "Extension": str(rng.randint(1000, 9999)),
            "Total Calls": total,
            "Answered Calls": answered,
            "% Answered Calls": round(answered / total * 100, 1) if total else 0,
            "Abandoned Calls": abandoned,
            "% Abandoned Calls": round(abandoned / total * 100, 1) if total else 0,
            "Avg No. of Agents Assigned": round(rng.uniform(1.5, 6.0), 1),
            "Avg No. of Agents Handling Calls": round(rng.uniform(0.2, 4.5), 1),
            "Avg Wait Time": round(rng.uniform(15, 180), 1),
            "Avg Talk Time": round(rng.uniform(60, 420), 1),
        })
    return pd.DataFrame(rows)


def generate_cdr(rng: random.Random, sc: Scenario, start: str, end: str) -> pd.DataFrame:
    start_d = datetime.fromisoformat(start)
    end_d = datetime.fromisoformat(end) + timedelta(days=1)
    span = (end_d - start_d).total_seconds()
    rows = []
    reasons = ["Deflection", "CallQueue", "ConsultativeTransfer", "CallForwardBusy", "CallForwardNoAnswer", ""]
    for i in range(sc.cdr_legs):
        ts = start_d + timedelta(seconds=rng.uniform(0, span))
        ctype = weighted_choice(rng, CALL_TYPES)
        if ctype == "SIP_INTERNATIONAL":
            if rng.random() > sc.intl_share / 0.05:
                ctype = "SIP_NATIONAL"
        user = rng.choice(AGENTS)
        loc = rng.choice(LOCATIONS)
        dur = 0 if (ctype == "SIP_INTERNATIONAL" and rng.random() < 0.15) else rng.randint(5, 2400)
        outcome = rng.choices(
            OUTCOME_REASONS,
            weights=[0.06, 0.04, 0.02, 0.88],
            k=1,
        )[0]
        rec_result = "failed" if rng.random() < sc.rec_fail_rate else (
            "success" if rng.random() < 0.12 else ""
        )
        rows.append({
            "Start time": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "Duration": dur,
            "User": user,
            "Location": loc,
            "Call type": ctype,
            "Related reason": rng.choice(reasons),
            "Call outcome reason": outcome,
            "Call Recording Result": rec_result,
            "Call Recording Trigger": rng.choice(["always", "always-pause-resume", ""]),
            "Answered": outcome == "Success",
            "Direction": rng.choice(["ORIGINATING", "TERMINATING", "ORIGINATING"]),
        })
    return pd.DataFrame(rows)


def generate_media_quality(rng: random.Random, sc: Scenario, cdr: pd.DataFrame) -> pd.DataFrame:
    sample = cdr.sample(n=min(len(cdr), max(200, len(cdr) // 2)), random_state=sc.seed)
    rows = []
    for _, row in sample.iterrows():
        poor = rng.random() < sc.poor_mq_share
        rows.append({
            "User Name": row["User"],
            "Start Time": row["Start time"],
            "Location": row["Location"],
            "Call Quality": "Poor" if poor else rng.choice(["Good", "Good", "Fair"]),
            "Duration(s)": int(row["Duration"]),
            "Audio Packet Loss (%)": round(rng.uniform(0.1, 4.5) if poor else rng.uniform(0, 0.8), 2),
            "Audio Latency (ms)": int(rng.uniform(120, 380) if poor else rng.uniform(20, 90)),
            "Call Type": row["Call type"],
        })
    return pd.DataFrame(rows)


def generate_connectivity(rng: random.Random, sc: Scenario) -> pd.DataFrame:
    rows = []
    total = rng.randint(95, 140)
    disc = sc.disconnected_devices
    for i in range(total):
        disconnected = i < disc
        rows.append({
            "Account name": f"endpoint-{i+1}",
            "Account type": rng.choice(["User", "User", "Place", "Virtual Line"]),
            "Email": f"user{i+1}@demo.example",
            "Location": rng.choice(LOCATIONS),
            "Country": rng.choice(["US", "US", "GB", "SG"]),
            "Connected endpoint": "Yes" if not disconnected else "No",
            "Primary connectivity": "Disconnected" if disconnected else rng.choice(["SIP", "PN"]),
            "Event type": "Registration" if not disconnected else "Unregistered",
        })
    return pd.DataFrame(rows)


def analyze(
    aa: pd.DataFrame, cq: pd.DataFrame, cdr: pd.DataFrame, mq: pd.DataFrame, conn: pd.DataFrame
) -> dict:
    tc = pd.to_numeric(aa["Total Calls"], errors="coerce").fillna(0)
    ans = pd.to_numeric(aa["Answered"], errors="coerce").fillna(0)
    aa_rate = float(ans.sum() / tc.sum() * 100) if tc.sum() else 0.0

    total_q = pd.to_numeric(cq["Total Calls"], errors="coerce").fillna(0).sum()
    aband = pd.to_numeric(cq["Abandoned Calls"], errors="coerce").fillna(0).sum()
    ans_q = pd.to_numeric(cq["Answered Calls"], errors="coerce").fillna(0).sum()
    abandon_rate = float(aband / total_q * 100) if total_q else 0.0
    queue_answer_rate = float(ans_q / total_q * 100) if total_q else 0.0

    deflections = int((cdr["Related reason"] == "Deflection").sum()) if not cdr.empty else 0
    unknown_ct = int(cdr["Call type"].astype(str).str.upper().eq("UNKNOWN").sum()) if not cdr.empty else 0

    poor = mq["Call Quality"].astype(str).str.lower().eq("poor").sum() if not mq.empty else 0
    mq_poor_rate = float(poor / len(mq) * 100) if len(mq) else 0.0

    total_min = float(pd.to_numeric(cdr["Duration"], errors="coerce").fillna(0).sum() / 60) if not cdr.empty else 0.0
    rec_failed = int(cdr["Call Recording Result"].astype(str).str.lower().eq("failed").sum()) if not cdr.empty else 0

    disconnected = int(
        conn["Primary connectivity"].astype(str).str.lower().str.contains("disconnect|unregistered").sum()
    ) if not conn.empty else 0

    cdr["_day"] = pd.to_datetime(cdr["Start time"], errors="coerce").dt.date
    daily = cdr.groupby("_day").size()
    peak_avg_ratio = float(daily.max() / daily.mean()) if len(daily) and daily.mean() else 1.0
    peak_day = str(daily.idxmax()) if len(daily) else "—"
    peak_legs = int(daily.max()) if len(daily) else 0

    refusal_mask = cdr["Call outcome reason"].astype(str) != "Success"
    refusals = int(refusal_mask.sum()) if not cdr.empty else 0
    refusal_rate = float(refusals / len(cdr) * 100) if len(cdr) else 0.0

    loc_vol = cdr.groupby("Location").size().sort_values(ascending=False)
    loc_pct = {k: round(v / len(cdr) * 100, 1) for k, v in loc_vol.head(5).items()}

    return {
        "aa_answer_rate": aa_rate,
        "abandon_rate": abandon_rate,
        "queue_answer_rate": queue_answer_rate,
        "deflections": deflections,
        "unknown_ct": unknown_ct,
        "mq_poor_rate": mq_poor_rate,
        "total_min": total_min,
        "rec_failed": rec_failed,
        "disconnected": disconnected,
        "peak_avg_ratio": peak_avg_ratio,
        "peak_day": peak_day,
        "peak_legs": peak_legs,
        "cdr_rows": len(cdr),
        "refusals": refusals,
        "refusal_rate": refusal_rate,
        "loc_pct": loc_pct,
        "s1": pct_status(aa_rate, 90, 70, high_is_good=True),
        "s2": pct_status(abandon_rate, 10, 30),
        "s3": "warn" if (deflections > 10 or unknown_ct > 0) else "good",
        "s4": pct_status(queue_answer_rate, 80, 60, high_is_good=True),
        "s5": pct_status(mq_poor_rate, 5, 15),
        "s6": "good",
        "s7": "good" if rec_failed == 0 else ("warn" if rec_failed <= 3 else "bad"),
        "s8": pct_status(disconnected, 0, 5),
        "s9": "warn" if peak_avg_ratio > 2.5 else "good",
    }


def build_manifest(sc: Scenario, start: str, end: str, m: dict, files: dict[str, str]) -> dict:
    return {
        "scenario": sc.slug,
        "title": sc.title,
        "org_name": sc.org_name,
        "period": {"start": start, "end": end},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
        "webex_report_templates": REPORT_TYPES,
        "data_files": files,
        "scorecard_derivation": [
            {"section": "§1 Reachability", "metric": "AA answer rate", "formula": "sum(Answered) / sum(Total Calls) from aa_summary CSV", "value": f"{m['aa_answer_rate']:.1f}%"},
            {"section": "§2 Abandonment", "metric": "Queue abandon rate", "formula": "sum(Abandoned Calls) / sum(Total Calls) from call_queue CSV", "value": f"{m['abandon_rate']:.1f}%"},
            {"section": "§3 Routing", "metric": "Deflections", "formula": "count(Related reason = Deflection) in CDR", "value": str(m["deflections"])},
            {"section": "§4 SLA", "metric": "Queue answer rate", "formula": "sum(Answered Calls) / sum(Total Calls) from call_queue CSV", "value": f"{m['queue_answer_rate']:.1f}%"},
            {"section": "§5 Quality", "metric": "Poor call rate", "formula": "count(Call Quality = Poor) / rows in media_quality CSV", "value": f"{m['mq_poor_rate']:.1f}%"},
            {"section": "§6 Usage", "metric": "Total minutes", "formula": "sum(Duration) / 60 from CDR", "value": f"{int(m['total_min'])}"},
            {"section": "§7 Recording", "metric": "Failed recordings", "formula": "count(Call Recording Result = failed) in CDR", "value": str(m["rec_failed"])},
            {"section": "§8 Trunk", "metric": "Disconnected endpoints", "formula": "count(Primary connectivity contains disconnect/unregistered) in connectivity CSV", "value": str(m["disconnected"])},
            {"section": "§9 Capacity", "metric": "Peak/avg day ratio", "formula": "max(daily CDR legs) / mean(daily CDR legs)", "value": f"{m['peak_avg_ratio']:.1f}×"},
        ],
        "row_counts": {k: files.get(f"{k}_rows") for k in REPORT_TYPES},
    }


def table_rows_aa(aa: pd.DataFrame) -> str:
    out = []
    for _, r in aa.iterrows():
        pct = r["% Answered"]
        st = "good" if pct >= 90 else ("warn" if pct >= 70 else "bad")
        out.append(
            f"<tr><td>{r['Auto Attendant']}</td><td>{r['Location']}</td>"
            f"<td>{int(r['Total Calls'])}</td><td>{int(r['Answered'])}</td>"
            f"<td>{int(r['Unanswered'])}</td><td>{pct}%</td><td>{pill(st)}</td></tr>"
        )
    return "\n".join(out)


def table_rows_cq(cq: pd.DataFrame) -> str:
    out = []
    for _, r in cq.iterrows():
        pct = r["% Answered Calls"]
        st = "good" if pct >= 80 else ("warn" if pct >= 60 else "bad")
        out.append(
            f"<tr><td>{r['Call Queue']}</td><td>{r['Location']}</td>"
            f"<td>{int(r['Total Calls'])}</td><td>{int(r['Answered Calls'])}</td>"
            f"<td>{int(r['Abandoned Calls'])}</td><td>{pct}%</td><td>{pill(st)}</td></tr>"
        )
    return "\n".join(out)


def render_report(
    sc: Scenario, period_label: str, m: dict,
    aa: pd.DataFrame, cq: pd.DataFrame, cdr: pd.DataFrame, manifest: dict,
) -> str:
    full = TEMPLATE.read_text(encoding="utf-8")
    css = full[full.find("<style>") : full.find("</style>") + 8]
    script = full[full.find("<script>") :]

    call_types = cdr.groupby("Call type").agg(legs=("Call type", "count"), minutes=("Duration", "sum")).reset_index()
    reasons = cdr[cdr["Related reason"].astype(str).str.len() > 0].groupby("Related reason").size().sort_values(ascending=False).head(8)
    refusals = cdr[cdr["Call outcome reason"] != "Success"].groupby("Call outcome reason").agg(
        count=("Call outcome reason", "count"),
        users=("User", lambda s: ", ".join(sorted(set(s))[:4])),
    ).reset_index()
    top_users = cdr.groupby("User")["Duration"].sum().sort_values(ascending=False).head(8)
    billable = cdr[cdr["Call type"].isin(["SIP_INBOUND", "SIP_NATIONAL", "SIP_MOBILE", "SIP_INTERNATIONAL"])]
    billable_min = int(billable["Duration"].sum() / 60)

    prov_rows = "".join(
        f"<tr><td>{d['section']}</td><td>{d['metric']}</td><td style='font-size:12px'>{d['formula']}</td>"
        f"<td><strong>{d['value']}</strong></td></tr>"
        for d in manifest["scorecard_derivation"]
    )

    loc_bars = ""
    for loc, pct in m["loc_pct"].items():
        loc_bars += (
            f'<div class="bar-row"><span class="bar-label">{loc}</span>'
            f'<div class="bar-track"><div class="bar-fill{" dominant" if pct > 35 else ""}" style="width:{pct}%"></div></div>'
            f'<span class="bar-pct">{pct}%</span></div>'
        )

    scorecard = ""
    cards = [
        (1, f"{m['aa_answer_rate']:.1f}%", "Reachability · AA answer rate", m["s1"]),
        (2, f"{m['abandon_rate']:.1f}%", "Abandonment · queue abandon rate", m["s2"]),
        (3, str(m["deflections"]), "Routing · deflection events", m["s3"]),
        (4, f"{m['queue_answer_rate']:.1f}%", "SLA · queue answer rate", m["s4"]),
        (5, f"{m['mq_poor_rate']:.1f}%", "Call quality · poor rate", m["s5"]),
        (6, f"{int(m['total_min'])}", "Cost & usage · total minutes", m["s6"]),
        (7, str(m["rec_failed"]), "Recording · failed", m["s7"]),
        (8, str(m["disconnected"]), "Trunk · disconnected", m["s8"]),
        (9, f"{m['peak_avg_ratio']:.1f}×", "Capacity · peak/avg ratio", m["s9"]),
    ]
    for num, val, sub, st in cards:
        name = sub.split("·")[0].strip()
        scorecard += f"""
  <div class="sc {st}" id="sc{num}" onclick="selectCard({num})">
    <div class="sc-num">§{num}</div>
    <div class="sc-name">{name}</div>
    <div class="sc-val {st}" id="sc{num}-val">{val}</div>
    <div class="sc-sub">{sub.split('·', 1)[-1].strip()}</div>
    <div class="badge {st}" id="sc{num}-badge">{badge(st)}</div>
  </div>"""

    ct_rows = "".join(
        f"<tr><td>{r['Call type']}</td><td>{int(r['legs'])}</td>"
        f"<td>{int(r['minutes']//60)}</td><td style='font-size:12px;color:var(--muted)'>From CDR</td></tr>"
        for _, r in call_types.iterrows()
    )
    reason_rows = "".join(
        f"<tr><td>{name}</td><td>{int(cnt)}</td><td>{pill('bad' if name=='Deflection' else 'good')}</td></tr>"
        for name, cnt in reasons.items()
    )
    ref_rows = "".join(
        f"<tr><td>{r['Call outcome reason']}</td><td>{int(r['count'])}</td>"
        f"<td>{r['users']}</td><td>{pill('bad' if r['Call outcome reason']=='UnassignedNumber' else 'warn')}</td></tr>"
        for _, r in refusals.iterrows()
    )
    user_rows = "".join(
        f"<tr><td>{user}</td><td>{dur/60:.1f}</td></tr>" for user, dur in top_users.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Webex Calling — {sc.title} · {period_label}</title>
{css}
</head>
<body>
<div style="background:#E6F8FD;border-bottom:1px solid #9DE5F7;color:#005E7D;padding:10px 16px;font-size:13px;text-align:center">
  <strong>Hackathon demo</strong> — synthetic Control Hub CSVs · scenario: <code>{sc.slug}</code> ·
  <a href="../index.html">All scenarios</a> ·
  <a href="../data/{sc.slug}/manifest.json">Data manifest (JSON)</a>
</div>
<div class="hdr">
  <div class="hdr-left">
    <h1>Webex Calling — Operations Report</h1>
    <p>Organization: <span id="org-name">{sc.org_name}</span> · Period: <span id="period">{period_label}</span></p>
  </div>
  <div class="hdr-right">
    <button class="btn btn-ghost" onclick="toggleAll()">Expand All</button>
    <button class="btn btn-white" onclick="window.print()">Print / Export</button>
  </div>
</div>
<div class="wrap">
<div class="hint">
  <span><strong>Explainable AI demo:</strong> Every scorecard metric is computed from downloadable CSV files that mirror real Webex Control Hub report exports. See §0 below for formulas and file names.</span>
</div>

<div class="section" id="s0">
  <div class="sec-hdr open" onclick="toggleSection('s0')">
    <div class="sec-dot good">0</div>
    <div class="sec-info">
      <div class="sec-title">§0 — Data Provenance</div>
      <div class="sec-sub">Where every number comes from · {m['cdr_rows']} CDR legs · {len(aa)} AAs · {len(cq)} queues</div>
    </div>
    <div class="badge good">🟢 Traceable</div>
    <div class="chevron open">›</div>
  </div>
  <div class="sec-body open" id="s0-body">
    <div class="meta-bar">
      <div class="meta-item">Scenario: <strong>{sc.title}</strong></div>
      <div class="meta-item">Seed: <strong>{sc.seed}</strong> (reproducible)</div>
      <div class="meta-item">Manifest: <strong><a href="../data/{sc.slug}/manifest.json">manifest.json</a></strong></div>
    </div>
    <div class="sub-label">Scorecard → source report → formula</div>
    <table>
      <thead><tr><th>Section</th><th>Metric</th><th>Formula (from CSV columns)</th><th>Value</th></tr></thead>
      <tbody>{prov_rows}</tbody>
    </table>
    <div class="sub-label">Download synthetic source CSVs</div>
    <p style="font-size:13px">These files use the same column headers as Webex Control Hub exports:
      <a href="../data/{sc.slug}/cdr_{manifest['period']['start']}_{manifest['period']['end']}.csv">CDR</a>,
      <a href="../data/{sc.slug}/call_queue_{manifest['period']['start']}_{manifest['period']['end']}.csv">Call Queue</a>,
      <a href="../data/{sc.slug}/aa_summary_{manifest['period']['start']}_{manifest['period']['end']}.csv">AA Summary</a>,
      <a href="../data/{sc.slug}/media_quality_{manifest['period']['start']}_{manifest['period']['end']}.csv">Media Quality</a>,
      <a href="../data/{sc.slug}/connectivity_{manifest['period']['start']}_{manifest['period']['end']}.csv">Connectivity</a>.
    </p>
  </div>
</div>

<div class="scorecard" id="scorecard">{scorecard}</div>

<div class="section" id="s1">
  <div class="sec-hdr" onclick="toggleSection('s1')">
    <div class="sec-dot {m['s1']}">1</div>
    <div class="sec-info"><div class="sec-title">§1 — Reachability</div>
    <div class="sec-sub">AA answer rate {m['aa_answer_rate']:.1f}% · {len(aa)} auto attendants</div></div>
    <div class="badge {m['s1']}">{badge(m['s1'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s1-body">
    <div class="meta-bar"><div class="meta-item">Source: <strong>AA Summary + Call Queue Stats</strong></div></div>
    <div class="sub-label">Auto Attendants</div>
    <table><thead><tr><th>Auto Attendant</th><th>Location</th><th>Total</th><th>Answered</th><th>Unanswered</th><th>% Ans</th><th>Status</th></tr></thead>
    <tbody>{table_rows_aa(aa)}</tbody></table>
    <div class="sub-label">Call Queues</div>
    <table><thead><tr><th>Queue</th><th>Location</th><th>Total</th><th>Answered</th><th>Abandoned</th><th>% Ans</th><th>Status</th></tr></thead>
    <tbody>{table_rows_cq(cq)}</tbody></table>
  </div>
</div>

<div class="section" id="s2">
  <div class="sec-hdr" onclick="toggleSection('s2')">
    <div class="sec-dot {m['s2']}">2</div>
    <div class="sec-info"><div class="sec-title">§2/4 — Queue Health</div>
    <div class="sec-sub">{m['abandon_rate']:.1f}% abandon · {m['queue_answer_rate']:.1f}% answer rate</div></div>
    <div class="badge {m['s2']}">{badge(m['s2'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s2-body">
    <div class="meta-bar"><div class="meta-item">Source: <strong>Call Queue Stats CSV</strong></div></div>
    <table><thead><tr><th>Queue</th><th>Location</th><th>Total</th><th>Abandoned</th><th>% Abandon</th><th>Avg agents handling</th></tr></thead>
    <tbody>{"".join(f"<tr><td>{r['Call Queue']}</td><td>{r['Location']}</td><td>{int(r['Total Calls'])}</td><td>{int(r['Abandoned Calls'])}</td><td>{r['% Abandoned Calls']}%</td><td>{r['Avg No. of Agents Handling Calls']}</td></tr>" for _, r in cq.iterrows())}</tbody></table>
  </div>
</div>

<div class="section" id="s3">
  <div class="sec-hdr" onclick="toggleSection('s3')">
    <div class="sec-dot {m['s3']}">3</div>
    <div class="sec-info"><div class="sec-title">§3 — Routing Correctness</div>
    <div class="sec-sub">{m['deflections']} deflections · {m['unknown_ct']} UNKNOWN types · {m['cdr_rows']} legs</div></div>
    <div class="badge {m['s3']}">{badge(m['s3'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s3-body">
    <div class="meta-bar"><div class="meta-item">Source: <strong>CDR</strong></div></div>
    <div class="sub-label">Call Types</div>
    <table><thead><tr><th>Type</th><th>Legs</th><th>Minutes</th><th>Note</th></tr></thead><tbody>{ct_rows}</tbody></table>
    <div class="sub-label">Related Reasons</div>
    <table><thead><tr><th>Reason</th><th>Count</th><th>Status</th></tr></thead><tbody>{reason_rows}</tbody></table>
  </div>
</div>

<div class="section" id="s5">
  <div class="sec-hdr" onclick="toggleSection('s5')">
    <div class="sec-dot {m['s5']}">5</div>
    <div class="sec-info"><div class="sec-title">§5 — Call Quality</div>
    <div class="sec-sub">{m['refusal_rate']:.1f}% refusal rate · {m['refusals']} refused legs</div></div>
    <div class="badge {m['s5']}">{badge(m['s5'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s5-body">
    <table><thead><tr><th>Outcome Reason</th><th>Count</th><th>Affected Users</th><th>Status</th></tr></thead><tbody>{ref_rows}</tbody></table>
  </div>
</div>

<div class="section" id="s6">
  <div class="sec-hdr" onclick="toggleSection('s6')">
    <div class="sec-dot {m['s6']}">6</div>
    <div class="sec-info"><div class="sec-title">§6 — Cost &amp; Usage</div>
    <div class="sec-sub">{int(m['total_min'])} total min · {billable_min} billable PSTN min</div></div>
    <div class="badge {m['s6']}">{badge(m['s6'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s6-body">
    <div class="usage-grid">
      <div class="usage-stat"><div class="big">{int(m['total_min'])}</div><div class="sub">Total minutes</div></div>
      <div class="usage-stat"><div class="big">{billable_min}</div><div class="sub">Billable PSTN minutes</div></div>
      <div class="usage-stat"><div class="big">{m['cdr_rows']}</div><div class="sub">CDR legs</div></div>
      <div class="usage-stat"><div class="big">{m['refusals']}</div><div class="sub">Refused legs</div></div>
    </div>
    <div class="sub-label">Top users by duration</div>
    <table><thead><tr><th>User</th><th>Minutes</th></tr></thead><tbody>{user_rows}</tbody></table>
  </div>
</div>

<div class="section" id="s7">
  <div class="sec-hdr" onclick="toggleSection('s7')">
    <div class="sec-dot {m['s7']}">7</div>
    <div class="sec-info"><div class="sec-title">§7 — Recording Compliance</div>
    <div class="sec-sub">{m['rec_failed']} failed recordings</div></div>
    <div class="badge {m['s7']}">{badge(m['s7'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s7-body">
    <div class="meta-bar"><div class="meta-item">Source: <strong>CDR recording fields</strong></div></div>
    <p>Failed recordings counted where <code>Call Recording Result = failed</code> in CDR export.</p>
  </div>
</div>

<div class="section" id="s8">
  <div class="sec-hdr" onclick="toggleSection('s8')">
    <div class="sec-dot {m['s8']}">8</div>
    <div class="sec-info"><div class="sec-title">§8 — Trunk Health</div>
    <div class="sec-sub">{m['disconnected']} disconnected endpoints</div></div>
    <div class="badge {m['s8']}">{badge(m['s8'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s8-body">
    <div class="meta-bar"><div class="meta-item">Source: <strong>Calling Connectivity CSV</strong></div></div>
  </div>
</div>

<div class="section" id="s9">
  <div class="sec-hdr" onclick="toggleSection('s9')">
    <div class="sec-dot {m['s9']}">9</div>
    <div class="sec-info"><div class="sec-title">§9 — Capacity Planning</div>
    <div class="sec-sub">Peak {m['peak_day']} = {m['peak_legs']} legs ({m['peak_avg_ratio']:.1f}× avg)</div></div>
    <div class="badge {m['s9']}">{badge(m['s9'])}</div><div class="chevron">›</div>
  </div>
  <div class="sec-body" id="s9-body">
    <div class="sub-label">Volume by location</div>
    {loc_bars}
  </div>
</div>

<div style="text-align:center;padding:24px 0 8px;font-size:12px;color:var(--muted)">
  {sc.org_name} · {period_label} · Synthetic demo · Top 5 AI Hackathon
</div>
</div>
{script}
</body>
</html>"""
    return html


def render_hub(summaries: list[dict]) -> str:
    cards = ""
    for s in summaries:
        cards += f"""
    <a class="card" href="reports/{s['slug']}.html">
      <h2>{s['title']}</h2>
      <p class="org">{s['org_name']}</p>
      <p class="tag">{s['tagline']}</p>
      <div class="stats">
        <span>{s['cdr_rows']:,} CDR legs</span>
        <span>AA {s['aa_rate']:.0f}%</span>
        <span>Abandon {s['abandon_rate']:.0f}%</span>
      </div>
      <p class="link">Open dashboard →</p>
    </a>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Webex Ops Report — Hackathon Demo Hub</title>
<style>
:root {{ --wx:#00BCEB; --wx-dark:#007FAD; --bg:#F0F4F8; --card:#fff; --text:#1B2A3B; --muted:#6B7A8D; }}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}}
.hdr{{background:linear-gradient(135deg,#005E7D,#00BCEB);color:#fff;padding:32px 24px;text-align:center}}
.hdr h1{{font-size:24px;margin-bottom:8px}}
.hdr p{{opacity:.9;font-size:15px;max-width:640px;margin:0 auto}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 16px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}}
.card{{background:var(--card);border-radius:12px;padding:24px;text-decoration:none;color:inherit;box-shadow:0 2px 12px rgba(0,0,0,.08);transition:transform .15s,box-shadow .15s;border-top:4px solid var(--wx)}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.12)}}
.card h2{{font-size:18px;margin-bottom:4px;color:var(--wx-dark)}}
.org{{font-size:13px;color:var(--muted);margin-bottom:8px}}
.tag{{font-size:14px;margin-bottom:16px}}
.stats{{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;margin-bottom:12px}}
.stats span{{background:#E6F8FD;color:var(--wx-dark);padding:4px 10px;border-radius:20px;font-weight:600}}
.link{{font-size:13px;font-weight:700;color:var(--wx-dark)}}
.prov{{background:#fff;border-radius:12px;padding:24px;margin-top:32px;box-shadow:0 2px 12px rgba(0,0,0,.06)}}
.prov h3{{margin-bottom:12px}}
.prov ol{{margin-left:20px;font-size:14px}}
.prov li{{margin:8px 0}}
</style>
</head>
<body>
<div class="hdr">
  <h1>Webex Calling Ops Report — AI Hackathon Demo</h1>
  <p>Top 5 project showcase. Three fully synthetic enterprises built from Webex Control Hub report schemas — every scorecard metric traceable to downloadable CSVs.</p>
</div>
<div class="wrap">
  <div class="grid">{cards}</div>
  <div class="prov">
    <h3>How the data works</h3>
    <ol>
      <li><strong>Generate CSVs</strong> — Synthetic exports matching real Webex report column headers (CDR, Call Queue, AA Summary, Media Quality, Connectivity).</li>
      <li><strong>Compute scorecard</strong> — Same formulas as production wxops <code>generate_misc_report.py</code> (sum/aggregate/count on CSV columns).</li>
      <li><strong>Render dashboard</strong> — Interactive HTML with §0 Data Provenance linking each metric to its source file and formula.</li>
      <li><strong>Reproducible</strong> — Each scenario uses a fixed random seed; re-run <code>generate_demo_reports.py</code> to regenerate.</li>
    </ol>
  </div>
</div>
</body>
</html>"""


def main() -> None:
    start, end, period_label = period()
    reports_dir = ROOT / "reports"
    data_root = ROOT / "data"
    reports_dir.mkdir(exist_ok=True)
    summaries = []

    for sc in SCENARIOS:
        rng = random.Random(sc.seed)
        aa = generate_aa_summary(rng, sc)
        cq = generate_call_queue(rng, sc)
        cdr = generate_cdr(rng, sc, start, end)
        mq = generate_media_quality(rng, sc, cdr)
        conn = generate_connectivity(rng, sc)
        m = analyze(aa, cq, cdr, mq, conn)

        out = data_root / sc.slug
        out.mkdir(parents=True, exist_ok=True)
        files: dict[str, str] = {}
        for prefix, df in [
            ("cdr", cdr), ("call_queue", cq), ("aa_summary", aa),
            ("media_quality", mq), ("connectivity", conn),
        ]:
            name = f"{prefix}_{start}_{end}.csv"
            path = out / name
            df.to_csv(path, index=False)
            files[prefix] = f"data/{sc.slug}/{name}"
            files[f"{prefix}_rows"] = len(df)

        manifest = build_manifest(sc, start, end, m, files)
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        html = render_report(sc, period_label, m, aa, cq, cdr, manifest)
        (reports_dir / f"{sc.slug}.html").write_text(html, encoding="utf-8")

        summaries.append({
            "slug": sc.slug,
            "title": sc.title,
            "org_name": sc.org_name,
            "tagline": sc.tagline,
            "cdr_rows": m["cdr_rows"],
            "aa_rate": m["aa_answer_rate"],
            "abandon_rate": m["abandon_rate"],
        })
        print(f"✓ {sc.slug}: {m['cdr_rows']} CDR legs, AA {m['aa_answer_rate']:.1f}%, abandon {m['abandon_rate']:.1f}%")

    (ROOT / "index.html").write_text(render_hub(summaries), encoding="utf-8")
    print(f"\nHub → {ROOT / 'index.html'}")


if __name__ == "__main__":
    main()
