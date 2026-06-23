"""Verified Business Insight slide values (May 2026 screenshots).

Used to sync spreadsheet rows for matching Customer org id. Monetary values are
stored as numbers (dollars) for TCV $ / AAR $ columns.
"""

from __future__ import annotations

from typing import Any

from .slide_layout import (
    FEATURE_FIELDS,
    HEADER_FIELDS,
    PROVISIONING_FIELDS,
    SUBSCRIPTION_FIELDS,
)

# Fields that must match between slide and spreadsheet when syncing
CORE_SLIDE_FIELDS = (
    "TCV $",
    "AAR $",
    "SL2",
    "Partner",
    "Sub #",
    "Sub term (months)",
    "Sub start date (MM/DD/YYYY)",
    "Collab AE/SE",
    "CSM Engagement Model (linked)",
    " (G/Y/R)",
)

STRUCTURED_SLIDE_FIELDS = (
    *SUBSCRIPTION_FIELDS,
    *PROVISIONING_FIELDS,
    *FEATURE_FIELDS,
    *HEADER_FIELDS,
)

VERIFIED_SLIDE_BY_ORG: dict[str, dict[str, Any]] = {
  # Berkeley County School District — slide 2026-05-19 (Jeremy Abrams)
    "fb078f9f-4332-4ace-8b1f-6a46313aa4ea": {
        "TCV $": 1_154_000,
        "AAR $": 261_696,
        "SL2": "US PS Market",
        "Partner": "Bridgetek Solutions LLC",
        "Sub #": "Sub963004",
        "Sub term (months)": "60",
        "Sub start date (MM/DD/YYYY)": "5/22/2025",
        "Collab AE/SE": "Peter Caterinicchia",
        "CSM Engagement Model (linked)": "Scale",
        "(G/Y/R)": "G",
        "Trend active users 90d": "UP +2.6% last 90 days",
        "Trend call volume 90d": "UP +52% last 90 days",
        "Lic Professional (used/entitled)": "4376/5193",
        "Lic Standard (used/entitled)": "0/0",
        "Lic Workspace (used/entitled)": "377/2164",
        "Active % of provisioned": "87%",
        "External calls": "35.8K out of 1.1M",
        "Meetings usage": "N/A",
        "Messaging usage": "1 active user; 1 message sent",
        "Auto Attendant count": "113",
        "Hunt Groups count": "9",
        "Call Queues count": "-",
        "Connected-UC (Y/N)": "Y",
        "Virtual Lines count": "96",
        "Data gathered by": "Jeremy Abrams",
        "Data gathered date": "2026-05-19",
    },
    # UT Medical Center — slide 2026-05-18 (Kenneth O)
    "40357664-235c-44a7-9127-3b4518eeb757": {
        "TCV $": 2_070_691,
        "AAR $": 500_611.56,
        "SL2": "USPS",
        "Partner": "Internetwork Engineering (Presidio)",
        "Sub #": "Sub2195655, Sub2195656, Sub535343",
        "Sub term (months)": "60",
        "Sub start date (MM/DD/YYYY)": "4/28/2025",
        "Collab AE/SE": "Kristen Dawson / Kyle Davenport",
        "CSM Engagement Model (linked)": "TAC Supported",
        "Service lines": "Meetings: EA | Calling: NU | WxCC",
        "Trend active users 90d": "UP +7.69% last 30 days",
        "Trend call volume 90d": "UP +11.2% last 30 days",
        "Lic Professional (used/entitled)": "40/105",
        "Lic Workspace (used/entitled)": "34/82",
        "Active % of provisioned": "See Active Lic Calling",
        "External calls": "22.9K out of 40.5K",
        "Meetings usage": "7 unique hosts; 29 total meetings",
        "Messaging usage": "21 active users; 1.5K messages sent",
        "Auto Attendant count": "14",
        "Hunt Groups count": "1",
        "Call Queues count": "3",
        "Connected-UC (Y/N)": "Y",
        "Virtual Lines count": "1",
        "Data gathered by": "Kenneth O",
        "Data gathered date": "2026-05-18",
    },
}

ALL_SLIDE_FIELDS = CORE_SLIDE_FIELDS + STRUCTURED_SLIDE_FIELDS
