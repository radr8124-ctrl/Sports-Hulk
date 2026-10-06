#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import shutil
import tempfile

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
CONTENT = ROOT / "sports_content"
DERIVED = CONTENT / "derived"
DRAFTS = DERIVED / "ARTICLE_DRAFTS.csv"
QUEUE = DERIVED / "ARTICLE_PUBLISH_QUEUE.csv"
PUBLISHED = CONTENT / "published"
AUDIT = CONTENT / "history" / "ARTICLE_STATUS_AUDIT.csv"

ALLOWED = {"DRAFT", "APPROVED", "REJECTED", "PUBLISHED"}


def now():
    return datetime.now(timezone.utc).isoformat()


def read():
    if not DRAFTS.exists():
        raise SystemExit("ARTICLE_DRAFTS.csv is missing.")
    return pd.read_csv(DRAFTS, low_memory=False)


def atomic_write(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.stem + "_",
        suffix=".csv",
        dir=str(path.parent),
    )
    os.close(fd)
    Path(tmp_name).unlink(missing_ok=True)
    tmp = Path(tmp_name)
    try:
        df.to_csv(tmp, index=False)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def write_queue(df):
    cols = [
        "draft_id", "sport", "article_type", "status",
        "title", "slug", "created_at", "updated_at",
        "approved_at", "published_at", "publish_destination",
        "publish_url", "requires_approval",
    ]
    use = [c for c in cols if c in df.columns]
    q = df[use].copy()
    order = pd.Categorical(
        q["status"].astype(str),
        categories=["APPROVED", "DRAFT", "REJECTED", "PUBLISHED"],
        ordered=True,
    )
    q["_order"] = order
    q = q.sort_values(
        ["_order", "updated_at"],
        ascending=[True, False],
    ).drop(columns=["_order"])
    atomic_write(q, QUEUE)


def audit(draft_id, action, prior_status, new_status, title):
    row = pd.DataFrame([{
        "changed_at": now(),
        "draft_id": draft_id,
        "action": action,
        "prior_status": prior_status,
        "new_status": new_status,
        "title": title,
        "actor": "OWNER_CHAT_APPROVAL",
    }])
    if AUDIT.exists():
        old = pd.read_csv(AUDIT, low_memory=False)
        row = pd.concat([old, row], ignore_index=True, sort=False)
    atomic_write(row, AUDIT)


def publish_file(row):
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    slug = str(row.get("slug") or row.get("draft_id"))
    path = PUBLISHED / f"{slug}.md"
    urls = []
    try:
        urls = json.loads(row.get("source_urls") or "[]")
    except Exception:
        urls = []

    sources = "\n".join(
        f"- {u}" for u in urls if u
    ) or "- Internal Sports HULK intelligence"

    text = (
        f"# {row.get('title', '')}\n\n"
        f"{row.get('dek', '')}\n\n"
        f"{row.get('body_markdown', '')}\n\n"
        "## Sources / provenance\n\n"
        f"{sources}\n\n"
        "_Published inside Sports HULK after owner approval._\n"
    )
    path.write_text(text, encoding="utf-8")
    return path


def change(draft_id, action):
    df = read()
    mask = df["draft_id"].astype(str).eq(str(draft_id))
    if not mask.any():
        raise SystemExit(f"Unknown draft_id: {draft_id}")

    idx = df.index[mask][0]
    prior = str(df.at[idx, "status"])
    title = str(df.at[idx, "title"])

    if action == "approve":
        if prior not in {"DRAFT", "REJECTED"}:
            raise SystemExit(f"Cannot approve from {prior}.")
        new = "APPROVED"
        df.at[idx, "approved_at"] = now()
        df.at[idx, "published_at"] = ""
        df.at[idx, "publish_destination"] = ""
        df.at[idx, "publish_url"] = ""

    elif action == "reject":
        if prior == "PUBLISHED":
            raise SystemExit("Unpublish before rejecting.")
        new = "REJECTED"
        df.at[idx, "approved_at"] = ""
        df.at[idx, "published_at"] = ""
        df.at[idx, "publish_destination"] = ""
        df.at[idx, "publish_url"] = ""

    elif action == "draft":
        if prior == "PUBLISHED":
            raise SystemExit("Unpublish before returning to draft.")
        new = "DRAFT"
        df.at[idx, "approved_at"] = ""
        df.at[idx, "published_at"] = ""
        df.at[idx, "publish_destination"] = ""
        df.at[idx, "publish_url"] = ""

    elif action == "publish":
        if prior != "APPROVED":
            raise SystemExit("Article must be APPROVED before publishing.")
        new = "PUBLISHED"
        record = df.loc[idx].to_dict()
        path = publish_file(record)
        df.at[idx, "published_at"] = now()
        df.at[idx, "publish_destination"] = "SPORTS_HULK_INTERNAL"
        df.at[idx, "publish_url"] = f"internal://sports-hulk/news/{df.at[idx, 'slug']}"
        print("PUBLISHED FILE:", path)

    elif action == "unpublish":
        if prior != "PUBLISHED":
            raise SystemExit("Article is not published.")
        new = "APPROVED"
        slug = str(df.at[idx, "slug"] or draft_id)
        (PUBLISHED / f"{slug}.md").unlink(missing_ok=True)
        df.at[idx, "published_at"] = ""
        df.at[idx, "publish_destination"] = ""
        df.at[idx, "publish_url"] = ""

    else:
        raise SystemExit(f"Unsupported action: {action}")

    if new not in ALLOWED:
        raise SystemExit("Invalid status.")

    df.at[idx, "status"] = new
    df.at[idx, "updated_at"] = now()
    atomic_write(df, DRAFTS)
    write_queue(df)
    audit(draft_id, action, prior, new, title)
    print(f"{draft_id}: {prior} -> {new}")
    print("TITLE:", title)


def list_items(status=None, sport=None, limit=30):
    df = read()
    if status:
        df = df[df["status"].astype(str).eq(status.upper())]
    if sport:
        df = df[df["sport"].astype(str).eq(sport.upper())]
    df = df.sort_values("updated_at", ascending=False).head(limit)
    cols = ["draft_id", "sport", "article_type", "status", "title"]
    print(df[cols].to_string(index=False))
    write_queue(read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--status")
    ap.add_argument("--sport")
    ap.add_argument("--limit", type=int, default=30)
    for action in ["approve", "reject", "draft", "publish", "unpublish"]:
        ap.add_argument(f"--{action}")
    args = ap.parse_args()

    actions = [
        (name, getattr(args, name))
        for name in ["approve", "reject", "draft", "publish", "unpublish"]
        if getattr(args, name)
    ]

    if len(actions) > 1:
        raise SystemExit("Use one status-changing action at a time.")

    if actions:
        change(actions[0][1], actions[0][0])
    else:
        list_items(args.status, args.sport, args.limit)


if __name__ == "__main__":
    main()
