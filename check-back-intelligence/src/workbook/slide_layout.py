"""PowerPoint slide layout → spreadsheet columns (three panels + header only)."""

from __future__ import annotations

# Header (above the three panels on the slide)
HEADER_FIELDS = (
    "Data gathered by",
    "Data gathered date",
)

# Subscription Review (cyan)
SUBSCRIPTION_FIELDS = (
    "AAR $",
    "Collab AE/SE",
    "Platforms",
    "Service lines",  # legacy header alias
    "Sub term (months)",
    "Subscription dates",
    "Trend active users 90d",
    "Trend call volume 90d",
    "Salesforce URL",
)

# Provisioning & Usage (orange)
PROVISIONING_FIELDS = (
    "Lic Professional (used/entitled)",
    "Lic Standard (used/entitled)",
    "Lic Workspace (used/entitled)",
    "Active % of provisioned",
    "External calls",
    "Meetings usage",
    "Messaging usage",
)

# Feature Use & Add-ons (magenta)
FEATURE_FIELDS = (
    "Auto Attendant count",
    "Hunt Groups count",
    "Call Queues count",
    "Connected-UC (Y/N)",
    "Virtual Lines count",
)

# KPI strip / bottom notes on slide — do not populate in spreadsheet
BELOW_PANEL_FIELDS = (
    "Total calls",
    "Answered calls %",
    "Calls busiest hour",
    "Recommended Actions",
    "CSM / Account Team notes",
)

STRUCTURED_COLUMNS = (
    *SUBSCRIPTION_FIELDS,
    *PROVISIONING_FIELDS,
    *FEATURE_FIELDS,
    *HEADER_FIELDS,
)
