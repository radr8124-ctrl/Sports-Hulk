from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from io import BytesIO, StringIO
from pathlib import Path
import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
from pypdf import PdfReader

from nfl_live.survivor_pool_import import (
    BASE,
    RAW,
    SNAPSHOTS,
    DERIVED,
    TEAM_MAP,
    normalize_pick,
    parse_entry_line,
)

ROOT = Path("/home/ubuntu/sports-hulk")

NFL_ABBR = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams", "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints",
    "NYG": "New York Giants", "NYJ": "New York Jets", "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers", "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

FULL_TEAMS = sorted(set(TEAM_MAP.values()) | set(NFL_ABBR.values()))

TEAM_ALIASES = {}
for mascot, full in TEAM_MAP.items():
    TEAM_ALIASES[mascot.upper()] = full
for abbr, full in NFL_ABBR.items():
    TEAM_ALIASES[abbr.upper()] = full
for full in FULL_TEAMS:
    TEAM_ALIASES[full.upper()] = full
    TEAM_ALIASES[full.upper().replace(" ", "")] = full
    TEAM_ALIASES[full.split()[-1].upper()] = full

# Common alternate labels.
TEAM_ALIASES.update({
    "SAN FRANCISCO": "San Francisco 49ers",
    "SANFRANCISCO": "San Francisco 49ers",
    "49ERS": "San Francisco 49ers",
    "LA CHARGERS": "Los Angeles Chargers",
    "LA RAMS": "Los Angeles Rams",
    "TAMPA": "Tampa Bay Buccaneers",
    "WASHINGTON": "Washington Commanders",
    "JACKSONVILLE": "Jacksonville Jaguars",
})


def _norm_header(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def _norm_team(value: object):
    raw = str(value or "").strip()
    if not raw or raw.lower() in {"nan", "none", "null", "-", "—"}:
        return None, None

    upper = re.sub(r"\s+", " ", raw.upper()).strip()
    marker = None

    # Preserve PDF/result-style markers where spreadsheets use X/Y.
    if upper.startswith("X") and upper[1:] in TEAM_ALIASES:
        marker = "X"
        upper = upper[1:]
    elif upper.startswith("Y") and upper[1:] in TEAM_ALIASES:
        marker = "Y"
        upper = upper[1:]

    # Strip result decorations without losing team text.
    cleaned = re.sub(r"\s*\((W|L|WIN|LOSS|LOST)\)\s*$", "", upper)
    cleaned = re.sub(r"\s+-\s+(W|L|WIN|LOSS|LOST)\s*$", "", cleaned)

    if cleaned in TEAM_ALIASES:
        return TEAM_ALIASES[cleaned], marker

    compact = cleaned.replace(" ", "")
    if compact in TEAM_ALIASES:
        return TEAM_ALIASES[compact], marker

    # Try old mascot parser last.
    team, old_marker, _ = normalize_pick(cleaned)
    if team:
        return team, marker or old_marker

    return None, marker


def _entry_name_parts(name: object):
    entry_name = re.sub(r"\s+", " ", str(name or "").strip())
    if not entry_name:
        return None

    tokens = entry_name.split()
    suffix = None
    participant = entry_name

    if tokens and re.fullmatch(r"\d{1,3}", tokens[-1]):
        suffix = tokens[-1].zfill(2)
        participant = " ".join(tokens[:-1]).strip()
        entry_name = f"{participant} {suffix}".strip()

    return {
        "entry_name": entry_name,
        "participant": participant,
        "entry_suffix": suffix,
    }


def _dedupe_entries(entries):
    dedup = {}
    for entry in entries:
        key = entry["entry_name"]
        existing = dedup.get(key)
        if existing is None or len(entry.get("picks") or []) > len(existing.get("picks") or []):
            dedup[key] = entry
    return list(dedup.values())


def parse_pdf_bytes(file_bytes: bytes):
    reader = PdfReader(BytesIO(file_bytes))
    entries = []
    page_payloads = []
    header_candidates = []

    for page_no, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        page_payloads.append((page_no, text))

        for line in text.splitlines():
            weeks = [
                int(value)
                for value in re.findall(
                    r"WEEK\s*#\s*(\d+)",
                    str(line).upper(),
                )
            ]
            if weeks:
                header_candidates.append(tuple(weeks))

    # Pool sheets can require multiple picks in the same NFL week.
    # Example: WEEK #1, WEEK #2, WEEK #3, WEEK #3, WEEK #4.
    # Preserve the actual header mapping instead of treating the fifth
    # pick column as "Week 5".
    header_weeks = []
    if header_candidates:
        counts = Counter(header_candidates)
        header_weeks = list(
            max(
                counts,
                key=lambda candidate: (
                    len(candidate),
                    counts[candidate],
                ),
            )
        )

    for page_no, text in page_payloads:
        for line in text.splitlines():
            parsed = parse_entry_line(
                line,
                page_no,
            )
            if not parsed:
                continue

            if header_weeks:
                occurrence = {}
                for index, pick in enumerate(
                    parsed.get("picks") or []
                ):
                    if index >= len(header_weeks):
                        break

                    week = int(
                        header_weeks[index]
                    )
                    occurrence[week] = (
                        occurrence.get(
                            week,
                            0,
                        )
                        + 1
                    )
                    pick["week_position"] = week
                    pick["week_pick_number"] = occurrence[
                        week
                    ]

            entries.append(parsed)

    entries = _dedupe_entries(entries)
    if not entries:
        raise ValueError(
            "No Survivor entries could be parsed from this PDF. "
            "The file may be scanned/image-only or use a layout the parser does not recognize."
        )

    current_week = (
        max(header_weeks)
        if header_weeks
        else max(
            (
                pick["week_position"]
                for entry in entries
                for pick in entry.get("picks", [])
            ),
            default=0,
        )
    )

    current_week_required_picks = (
        header_weeks.count(
            current_week
        )
        if (
            header_weeks
            and current_week
        )
        else None
    )

    return entries, {
        "pages": len(reader.pages),
        "sheet_names": [],
        "format": "PDF",
        "week_columns": header_weeks,
        "current_week": current_week,
        "current_week_required_picks": current_week_required_picks,
    }


def _xlsx_rows(file_bytes: bytes):
    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

    with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))

        wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rels = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rel_root.findall(PKG_REL_NS + "Relationship")
        }

        sheets = []
        for sheet in wb_root.find(NS + "sheets"):
            name = sheet.attrib.get("name", "Sheet")
            rid = sheet.attrib.get(REL_NS + "id")
            target = rels.get(rid, "")
            if not target.startswith("/"):
                target = "xl/" + target.lstrip("/")
            else:
                target = target.lstrip("/")
            sheets.append((name, target))

        result = []
        for name, target in sheets:
            if target not in zf.namelist():
                continue
            root = ET.fromstring(zf.read(target))
            rows = []
            for row in root.iter(NS + "row"):
                values = {}
                for cell in row.findall(NS + "c"):
                    ref = cell.attrib.get("r", "")
                    col = re.match(r"[A-Z]+", ref)
                    if not col:
                        continue
                    col_letters = col.group(0)
                    col_index = 0
                    for ch in col_letters:
                        col_index = col_index * 26 + (ord(ch) - ord("A") + 1)
                    col_index -= 1

                    ctype = cell.attrib.get("t")
                    value = None
                    if ctype == "inlineStr":
                        node = cell.find(NS + "is")
                        if node is not None:
                            value = "".join(t.text or "" for t in node.iter(NS + "t"))
                    else:
                        vnode = cell.find(NS + "v")
                        if vnode is not None:
                            raw = vnode.text or ""
                            if ctype == "s":
                                try:
                                    value = shared[int(raw)]
                                except Exception:
                                    value = raw
                            else:
                                value = raw
                    values[col_index] = value

                if values:
                    width = max(values) + 1
                    rows.append([values.get(i) for i in range(width)])

            if rows:
                result.append((name, rows))

        return result


def _csv_rows(file_bytes: bytes):
    text = file_bytes.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except Exception:
        dialect = csv.excel
    reader = csv.reader(StringIO(text), dialect)
    return [list(row) for row in reader if any(str(x).strip() for x in row)]


def _rows_to_frame(rows):
    if not rows:
        return pd.DataFrame()

    # Locate a likely header row in the first 15 rows.
    header_idx = 0
    for i, row in enumerate(rows[:15]):
        headers = [_norm_header(x) for x in row]
        joined = " ".join(headers)
        if (
            any(h in {"name", "entry", "entry_name", "participant"} for h in headers)
            or ("week" in joined and "name" in joined)
        ):
            header_idx = i
            break

    header = [_norm_header(x) or f"column_{i+1}" for i, x in enumerate(rows[header_idx])]
    width = len(header)
    data = []
    for row in rows[header_idx + 1:]:
        padded = list(row[:width]) + [None] * max(0, width - len(row))
        if any(str(x or "").strip() for x in padded):
            data.append(padded[:width])

    return pd.DataFrame(data, columns=header)


def _find_name_column(columns):
    preferred = [
        "entry_name", "entry", "name", "participant", "player_name",
        "pool_entry", "entrant", "member",
    ]
    for col in preferred:
        if col in columns:
            return col
    for col in columns:
        if "name" in col or "entry" in col:
            return col
    return None


def _week_from_col(col):
    text = str(col)
    patterns = [
        r"^week_?(\d+)$",
        r"^wk_?(\d+)$",
        r"^w_?(\d+)$",
        r"^pick_?(\d+)$",
        r"^(\d+)$",
    ]
    for pattern in patterns:
        m = re.match(pattern, text)
        if m:
            return int(m.group(1))
    return None


def _parse_wide_frame(df, source_label):
    columns = list(df.columns)
    name_col = _find_name_column(columns)
    if not name_col:
        raise ValueError("Could not find an Entry/Name column.")

    week_cols = []
    for col in columns:
        week = _week_from_col(col)
        if week is not None:
            week_cols.append((week, col))
    week_cols.sort()

    if not week_cols:
        raise ValueError(
            "Could not find Week 1 / Week 2 / Week 3 style columns."
        )

    marker_cols = {
        _week_from_col(col.replace("result_", "").replace("status_", "")): col
        for col in columns
        if col.startswith("result_") or col.startswith("status_")
    }

    entries = []
    for row_num, row in df.iterrows():
        parts = _entry_name_parts(row.get(name_col))
        if not parts:
            continue

        picks = []
        for week, col in week_cols:
            team, marker = _norm_team(row.get(col))
            if not team:
                continue

            raw_marker = marker
            status_col = marker_cols.get(week)
            if status_col:
                status = str(row.get(status_col) or "").strip().upper()
                if status in {"LOSS", "LOST", "L", "ELIMINATED", "X"}:
                    raw_marker = "X"
                elif status in {"WIN", "W", "SURVIVED", "Y"}:
                    raw_marker = "Y"

            picks.append({
                "week_position": week,
                "team": team,
                "marker": raw_marker,
                "raw_token": str(row.get(col) or "").strip(),
            })

        if picks:
            entries.append({
                **parts,
                "page": None,
                "raw_line": f"{source_label} row {row_num + 2}",
                "picks": picks,
            })

    return entries


def _parse_long_frame(df, source_label):
    columns = list(df.columns)
    name_col = _find_name_column(columns)

    week_col = next(
        (c for c in columns if c in {"week", "week_number", "week_position", "wk"}),
        None,
    )
    team_col = next(
        (c for c in columns if c in {"team", "pick", "selection", "team_name"}),
        None,
    )
    result_col = next(
        (c for c in columns if c in {"result", "status", "marker", "outcome"}),
        None,
    )

    if not name_col or not week_col or not team_col:
        raise ValueError("Long-format spreadsheet needs Entry/Name, Week, and Team/Pick columns.")

    grouped = {}
    for row_num, row in df.iterrows():
        parts = _entry_name_parts(row.get(name_col))
        if not parts:
            continue

        try:
            week = int(float(str(row.get(week_col)).strip()))
        except Exception:
            continue

        team, marker = _norm_team(row.get(team_col))
        if not team:
            continue

        if result_col:
            status = str(row.get(result_col) or "").strip().upper()
            if status in {"LOSS", "LOST", "L", "ELIMINATED", "X"}:
                marker = "X"
            elif status in {"WIN", "W", "SURVIVED", "Y"}:
                marker = "Y"

        key = parts["entry_name"]
        if key not in grouped:
            grouped[key] = {
                **parts,
                "page": None,
                "raw_line": f"{source_label}",
                "picks": [],
            }

        grouped[key]["picks"].append({
            "week_position": week,
            "team": team,
            "marker": marker,
            "raw_token": str(row.get(team_col) or "").strip(),
        })

    for entry in grouped.values():
        entry["picks"] = sorted(entry["picks"], key=lambda x: x["week_position"])

    return list(grouped.values())


def _parse_frame(df, source_label):
    df = df.copy()
    df.columns = [_norm_header(c) for c in df.columns]

    columns = set(df.columns)
    long_like = (
        _find_name_column(list(df.columns)) is not None
        and any(c in columns for c in {"week", "week_number", "week_position", "wk"})
        and any(c in columns for c in {"team", "pick", "selection", "team_name"})
    )

    if long_like:
        return _parse_long_frame(df, source_label), "LONG"

    return _parse_wide_frame(df, source_label), "WIDE"


def parse_spreadsheet_bytes(file_bytes: bytes, filename: str):
    ext = Path(filename).suffix.lower()
    sheet_entries = []
    sheet_names = []
    layouts = {}

    if ext == ".csv":
        frames = [("CSV", _rows_to_frame(_csv_rows(file_bytes)))]
    elif ext == ".xlsx":
        frames = [
            (sheet_name, _rows_to_frame(rows))
            for sheet_name, rows in _xlsx_rows(file_bytes)
        ]
    elif ext == ".xls":
        raise ValueError(
            "Legacy .xls files are not supported yet. Save the workbook as .xlsx or CSV and upload it again."
        )
    else:
        raise ValueError(f"Unsupported spreadsheet type: {ext}")

    errors = []
    for sheet_name, df in frames:
        if df.empty:
            continue
        sheet_names.append(sheet_name)
        try:
            parsed, layout = _parse_frame(df, sheet_name)
            if parsed:
                sheet_entries.extend(parsed)
                layouts[sheet_name] = layout
        except ValueError as exc:
            errors.append(f"{sheet_name}: {exc}")

    entries = _dedupe_entries(sheet_entries)
    if not entries:
        detail = "; ".join(errors[:4])
        raise ValueError(
            "No Survivor entries could be parsed from the spreadsheet."
            + (f" {detail}" if detail else "")
        )

    return entries, {
        "pages": None,
        "sheet_names": sheet_names,
        "layouts": layouts,
        "format": ext.lstrip(".").upper(),
        "warnings": errors,
    }


def parse_upload(file_bytes: bytes, filename: str):
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        entries, meta = parse_pdf_bytes(file_bytes)
    elif ext in {".xlsx", ".xls", ".csv"}:
        entries, meta = parse_spreadsheet_bytes(file_bytes, filename)
    else:
        raise ValueError("Supported files: PDF, XLSX, XLS, CSV.")

    max_week = max(
        (pick["week_position"] for entry in entries for pick in entry.get("picks", [])),
        default=0,
    )

    marker_counts = Counter(
        pick.get("marker")
        for entry in entries
        for pick in entry.get("picks", [])
        if pick.get("marker")
    )

    return {
        "filename": filename,
        "sha256": hashlib.sha256(file_bytes).hexdigest(),
        "entry_count": len(entries),
        "pick_rows": sum(len(entry.get("picks") or []) for entry in entries),
        "max_week": max_week,
        "eliminated_markers": int(marker_counts.get("X", 0)),
        "survived_markers": int(marker_counts.get("Y", 0)),
        "entries": entries,
        "meta": meta,
    }


def _write_frame_atomic(df: pd.DataFrame, csv_path: Path, parquet_path: Path | None = None):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temp_csv = csv_path.with_suffix(csv_path.suffix + ".tmp")
    df.to_csv(temp_csv, index=False)
    temp_csv.replace(csv_path)

    if parquet_path is not None:
        temp_parquet = parquet_path.with_suffix(parquet_path.suffix + ".tmp")
        df.to_parquet(temp_parquet, index=False)
        temp_parquet.replace(parquet_path)


def commit_preview(preview: dict, file_bytes: bytes):
    entries = preview["entries"]
    filename = preview["filename"]
    sha = preview["sha256"]
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    backup_dir = BASE / "backups" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_files = [
        "SURVIVOR_POOL_LEDGER.csv",
        "SURVIVOR_POOL_LEDGER.parquet",
        "SURVIVOR_POOL_CURRENT.csv",
        "SURVIVOR_POOL_CURRENT.parquet",
        "SURVIVOR_POOL_OWNERSHIP.csv",
        "SURVIVOR_POOL_OWNERSHIP.parquet",
        "ANNIE_G_POOL_ENTRIES.csv",
        "LATEST_OFFICIAL_POOL.json",
    ]
    for name in backup_files:
        source = DERIVED / name
        if source.exists():
            shutil.copy2(source, backup_dir / name)

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
    raw_path = RAW / f"{stamp}_{safe_name}"
    raw_path.write_bytes(file_bytes)

    snapshot = {
        "imported_at": now.isoformat(),
        "source_filename": filename,
        "source_sha256": sha,
        "page_count": preview.get("meta", {}).get("pages"),
        "sheet_names": preview.get("meta", {}).get("sheet_names", []),
        "spreadsheet_layouts": preview.get("meta", {}).get("layouts", {}),
        "source_format": preview.get("meta", {}).get("format"),
        "entry_count": len(entries),
        "entries": entries,
    }

    snapshot_path = SNAPSHOTS / f"SURVIVOR_POOL_{stamp}.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2))

    ledger_rows = []
    state_rows = []

    for entry in entries:
        picks = sorted(entry.get("picks") or [], key=lambda x: x["week_position"])

        for pick in picks:
            ledger_rows.append({
                "entry_name": entry["entry_name"],
                "participant": entry["participant"],
                "entry_suffix": entry["entry_suffix"],
                "week_position": pick["week_position"],
                "week_pick_number": int(
                    pick.get(
                        "week_pick_number"
                    )
                    or 1
                ),
                "team": pick["team"],
                "marker": pick.get("marker"),
                "raw_token": pick.get("raw_token"),
                "page": entry.get("page"),
                "source_filename": filename,
                "imported_at": snapshot["imported_at"],
            })

        markers = [p.get("marker") for p in picks if p.get("marker")]
        used = [p["team"] for p in picks]

        state_rows.append({
            "entry_name": entry["entry_name"],
            "participant": entry["participant"],
            "entry_suffix": entry["entry_suffix"],
            "status": "ELIMINATED" if "X" in markers else "ACTIVE_OR_UNCONFIRMED",
            "weeks_recorded": len(picks),
            "used_teams": " | ".join(used),
            "last_pick": used[-1] if used else None,
            "page": entry.get("page"),
            "source_filename": filename,
            "imported_at": snapshot["imported_at"],
        })

    ledger = pd.DataFrame(ledger_rows)
    state = pd.DataFrame(state_rows)

    ownership_rows = []
    if not ledger.empty:
        group_cols = [
            "week_position",
            "week_pick_number",
        ]

        for (
            week,
            pick_number,
        ), frame in ledger.groupby(
            group_cols
        ):
            total = len(frame)
            counts = Counter(
                frame["team"]
            )

            for team, count in counts.items():
                ownership_rows.append({
                    "week_position": int(week),
                    "week_pick_number": int(pick_number),
                    "team": team,
                    "pick_count": int(count),
                    "pool_rows_with_pick": int(total),
                    "pick_share_pct": round(count / total * 100, 2),
                })

    ownership = pd.DataFrame(ownership_rows)

    _write_frame_atomic(
        ledger,
        DERIVED / "SURVIVOR_POOL_LEDGER.csv",
        DERIVED / "SURVIVOR_POOL_LEDGER.parquet",
    )
    _write_frame_atomic(
        state,
        DERIVED / "SURVIVOR_POOL_CURRENT.csv",
        DERIVED / "SURVIVOR_POOL_CURRENT.parquet",
    )
    _write_frame_atomic(
        ownership,
        DERIVED / "SURVIVOR_POOL_OWNERSHIP.csv",
        DERIVED / "SURVIVOR_POOL_OWNERSHIP.parquet",
    )

    annie = state[state["participant"].astype(str).str.upper().eq("ANNIE G")].copy()
    _write_frame_atomic(
        annie,
        DERIVED / "ANNIE_G_POOL_ENTRIES.csv",
        None,
    )

    active_or_unconfirmed = int(
        (state["status"].astype(str) != "ELIMINATED").sum()
    ) if not state.empty else 0
    eliminated_entries = int(
        (state["status"].astype(str) == "ELIMINATED").sum()
    ) if not state.empty else 0

    meta = preview.get(
        "meta",
        {},
    )

    pool_week = int(
        meta.get(
            "current_week"
        )
        or preview.get(
            "max_week"
        )
        or 0
    )

    required_picks = meta.get(
        "current_week_required_picks"
    )

    if required_picks is not None:
        required_picks = int(
            required_picks
        )

    rule_status = (
        "CONFIRMED_FROM_IMPORTED_POOL_HEADER"
        if required_picks is not None
        else "IMPORTED_POOL_FILE_REVIEW_REQUIRED"
    )

    latest = {
        "imported_at": snapshot["imported_at"],
        "source_filename": filename,
        "source_sha256": sha,
        "source_format": snapshot["source_format"],
        "parsed_entries": len(entries),
        "ledger_rows": len(ledger),
        "max_week_in_file": int(preview.get("max_week") or 0),
        "pool_week": pool_week,
        "week_columns": meta.get("week_columns") or [],
        "imported_active_or_unconfirmed": active_or_unconfirmed,
        "imported_eliminated_entries": eliminated_entries,
        "current_week_required_picks": required_picks,
        "current_week_rule_status": rule_status,
        "whole_pool_import": True,
        "personal_entry_state_preserved": True,
        "snapshot_path": str(snapshot_path),
    }
    (DERIVED / "LATEST_OFFICIAL_POOL.json").write_text(
        json.dumps(
            latest,
            indent=2,
        )
    )

    # The imported pool header is authoritative for the current week's
    # pick-count rule. Sync only that rule into personal entry state;
    # never replace the user's saved picks or used-team history.
    personal_entries_path = (
        ROOT
        / "nfl_live"
        / "derived"
        / "SURVIVOR_ENTRIES.json"
    )

    if (
        pool_week
        and personal_entries_path.exists()
    ):
        try:
            personal = json.loads(
                personal_entries_path.read_text()
            )
            personal[
                "pool_current_week"
            ] = pool_week
            personal[
                "official_pool_state_updated_at"
            ] = snapshot[
                "imported_at"
            ]

            for entry in (
                personal.get(
                    "entries"
                )
                or {}
            ).values():
                if not isinstance(
                    entry,
                    dict,
                ):
                    continue

                if int(
                    entry.get(
                        "current_week"
                    )
                    or 0
                ) != pool_week:
                    continue

                key = (
                    "week_"
                    + str(
                        pool_week
                    )
                )
                block = entry.get(
                    key
                )

                if not isinstance(
                    block,
                    dict,
                ):
                    block = {}

                block[
                    "required_picks"
                ] = required_picks
                block[
                    "rule_status"
                ] = rule_status
                block[
                    "official_pool_sheet_confirmed"
                ] = (
                    required_picks
                    is not None
                )
                entry[
                    key
                ] = block

            fd, temp_name = tempfile.mkstemp(
                prefix="SURVIVOR_ENTRIES.pool.",
                suffix=".tmp",
                dir=str(
                    personal_entries_path.parent
                ),
                text=True,
            )

            try:
                with os.fdopen(
                    fd,
                    "w",
                ) as fh:
                    json.dump(
                        personal,
                        fh,
                        indent=2,
                    )
                    fh.write(
                        "\n"
                    )
                    fh.flush()
                Path(
                    temp_name
                ).replace(
                    personal_entries_path
                )
            finally:
                if Path(
                    temp_name
                ).exists():
                    Path(
                        temp_name
                    ).unlink()

        except Exception:
            # Whole-pool import remains valid even if personal rule
            # synchronization cannot be completed. The UI will fall
            # back to LATEST_OFFICIAL_POOL metadata.
            pass

    return {
        "source_filename": filename,
        "entries": len(entries),
        "ledger_rows": len(ledger),
        "ownership_rows": len(ownership),
        "max_week": int(preview.get("max_week") or 0),
        "pool_week": pool_week,
        "current_week_required_picks": required_picks,
        "snapshot_path": str(snapshot_path),
        "personal_entry_state_preserved": True,
    }
