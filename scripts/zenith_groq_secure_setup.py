#!/usr/bin/env python3
"""One-time GroqCloud Free API-key entry, performed ONLY in the owner's SSH TTY.

No network, no billing calls, no key echo, no CLI key argument, no logs.
The resulting .env file is gitignored and mode 0600; the owner must verify
Free/unbilled/no payment method in GroqCloud before this command is run.
"""
from __future__ import annotations

import getpass
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DEST=Path("/home/ubuntu/sports-hulk/commercial_web/.env.groq_shadow")
KEY_FORMAT=re.compile(r"^gsk_[A-Za-z0-9_-]{16,196}$")


def install_credential(path, secret_key, free_ack, *, when=None):
    """Fail closed; create an owner-only secret file once, no replacement."""
    if free_ack!="FREE":
        raise ValueError("free_plan_confirmation_required")
    if not isinstance(secret_key,str) or not KEY_FORMAT.fullmatch(secret_key):
        raise ValueError("invalid_groq_key")
    date=when or datetime.now(timezone.utc)
    if date.tzinfo is None:
        raise ValueError("confirmation_date_requires_timezone")
    checked=date.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    path=Path(path)
    if path.is_symlink() or path.exists():
        raise FileExistsError("groq_credentials_already_exist_not_replaced")
    if not path.parent.is_dir():
        raise ValueError("protected_directory_missing")

    content=(
        "ZENITH_GROQ_ACCOUNT_TIER=FREE_UNBILLED\n"
        "ZENITH_GROQ_ACCOUNT_NO_PAYMENT_METHOD=1\n"
        "ZENITH_GROQ_ACCOUNT_USER_CONFIRMED=1\n"
        "ZENITH_GROQ_ACCOUNT_CHECKED_AT="+checked+"\n"
        "GROQ_API_KEY="+secret_key+"\n"
    )
    # O_EXCL protects existing secrets; O_NOFOLLOW blocks symlink redirects.
    original_mask=os.umask(0o077)
    try:
        flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0)
        fd=os.open(str(path),flags,0o600)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.chmod(path,0o600)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
    finally:
        os.umask(original_mask)
    return path


def prompt_and_install(*, path=DEFAULT_DEST, is_tty=None,
                       ask_plan=input, read_secret=getpass.getpass):
    """The key must be entered by a human using their own interactive SSH session."""
    terminal=sys.stdin.isatty() and sys.stdout.isatty() if is_tty is None else is_tty
    if not terminal:
        raise RuntimeError("interactive_terminal_required")
    print("GroqCloud: verify your account is Free with NO payment method.")
    print("This command will NOT call the API or enable a paid tier.")
    print("Do not paste the API key into ChatGPT, chat messages, or shell command arguments.")
    acknowledgement=ask_plan("Type FREE if verified, or anything else to cancel: ").strip()
    if acknowledgement!="FREE":
        raise ValueError("free_plan_confirmation_required")
    secret=read_secret("Paste the new Groq API key (input stays hidden): ")
    return install_credential(path,secret,acknowledgement)


def main():
    try:
        target=prompt_and_install()
    except (ValueError,RuntimeError,FileExistsError,KeyboardInterrupt,OSError) as err:
        print("Groq credential setup stopped: "+str(err),file=sys.stderr)
        return 2
    print("Groq Free credential saved securely (0600), not displayed.")
    print("No API requests were made. Tell ChatGPT: 'Groq key saved securely'.")
    return 0


if __name__=="__main__":
    sys.exit(main())
