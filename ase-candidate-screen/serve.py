"""Serve the ASE preview dashboard on localhost only."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from color_workbook import load_rows, read_names, select_rows, write_colored
from rules import (
    COLORS,
    graduation_term,
    linkedin_search_url,
    primary_skill,
    score_display,
    score_key,
    skill_tags,
    status_key,
)

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard" / "index.html"
HOST = "127.0.0.1"

NAME_INDEX = 1
GRAD_INDEX = 2
SKILL_INDEX = 3
CITY_INDEX = 4
SCORE_INDEX = 8
NOTES_INDEX = 11
STATUS_INDEX = 13


def candidate_payload(row: tuple) -> dict:
    skills = row[SKILL_INDEX]
    status = row[STATUS_INDEX]
    graduation = row[GRAD_INDEX]
    score = row[SCORE_INDEX]
    return {
        "id": "" if row[0] is None else str(row[0]).strip(),
        "name": "" if row[NAME_INDEX] is None else str(row[NAME_INDEX]).strip(),
        "linkedin": linkedin_search_url(row[NAME_INDEX]),
        "graduation": "" if graduation is None else str(graduation).strip(),
        "graduationTerm": graduation_term(graduation),
        "city": "" if row[CITY_INDEX] is None else str(row[CITY_INDEX]).strip(),
        "skills": "" if skills is None else str(skills).strip(),
        "skillTags": skill_tags(skills),
        "primarySkill": primary_skill(skills),
        "notes": "" if row[NOTES_INDEX] is None else str(row[NOTES_INDEX]).strip(),
        "score": score_display(score),
        "scoreKey": score_key(score),
        "status": "" if status is None else str(status).strip(),
        "statusKey": status_key(status),
    }


def build_payload(workbook: Path, names: list[str] | None) -> dict:
    _header, data = load_rows(workbook)
    chosen = select_rows(data, names)
    return {
        "preview": names is not None,
        "shown": len(chosen),
        "totalInFile": len(data),
        "colors": COLORS,
        "candidates": [candidate_payload(row) for row in chosen],
    }


def make_handler(payload: dict):
    body = json.dumps(payload).encode("utf-8")
    html = DASHBOARD.read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            print(f"{self.address_string()} {fmt % args}")

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/candidates":
                self._send(body, "application/json; charset=utf-8")
                return
            if path in ("/", "/index.html"):
                self._send(html, "text/html; charset=utf-8")
                return
            self.send_error(404)

        def _send(self, content: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local ASE candidate dashboard.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--colored-output",
        type=Path,
        default=ROOT / "output" / "ASE-colored.xlsx",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--names-file", type=Path)
    mode.add_argument("--all", action="store_true")
    args = parser.parse_args()

    names = None if args.all else read_names(args.names_file)
    count = write_colored(args.workbook, args.colored_output, names)
    payload = build_payload(args.workbook, names)
    if payload["shown"] != count:
        raise SystemExit("Colored workbook and dashboard counts do not match")
    server = ThreadingHTTPServer((HOST, args.port), make_handler(payload))
    print(f"Dashboard http://{HOST}:{args.port}  ({count} candidates)")
    print(f"Colored workbook {args.colored_output}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")


if __name__ == "__main__":
    main()
