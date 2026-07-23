#!/usr/bin/env python3
import argparse
import html
import json
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

REFURBISHED_URL = "https://www.apple.com/hk/shop/refurbished/watch"
DEFAULT_MODEL = "Apple Watch SE 3 GPS, 40mm"
DEFAULT_STATE_FILE = ".apple_watch_seen.json"


@dataclass(frozen=True)
class Listing:
    title: str
    url: str


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def fetch_page(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def _strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_watch_listings(page_html: str) -> list[Listing]:
    listings: dict[str, Listing] = {}

    anchor_pattern = re.compile(
        r'<a[^>]+href="([^"]*/shop/product/[^"]+)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    for href, content in anchor_pattern.findall(page_html):
        title = _strip_html(content)
        if title:
            listings[href] = Listing(title=title, url=href)

    json_patterns = (
        re.compile(
            r'"url":"(https:(?:\\\\/|/){2}www\.apple\.com(?:\\\\/|/)hk(?:\\\\/|/)shop(?:\\\\/|/)product(?:\\\\/|/)[^"]+)"[^}]*?"title":"([^"]+)"',
            re.IGNORECASE,
        ),
        re.compile(
            r'"title":"([^"]+)"[^}]*?"url":"(https:(?:\\\\/|/){2}www\.apple\.com(?:\\\\/|/)hk(?:\\\\/|/)shop(?:\\\\/|/)product(?:\\\\/|/)[^"]+)"',
            re.IGNORECASE,
        ),
    )
    for pattern in json_patterns:
        for first, second in pattern.findall(page_html):
            raw_url, raw_title = (first, second) if first.startswith("https:") else (second, first)
            url = raw_url.replace("\\/", "/")
            title = html.unescape(raw_title)
            listings[url] = Listing(title=title, url=url)

    return list(listings.values())


def filter_listings_by_models(listings: Iterable[Listing], models: Iterable[str]) -> list[Listing]:
    normalized_models = [normalize_text(model) for model in models if model.strip()]
    if not normalized_models:
        return []

    matches: list[Listing] = []
    for listing in listings:
        normalized_title = normalize_text(listing.title)
        if any(model in normalized_title for model in normalized_models):
            matches.append(listing)
    return matches


def load_seen_urls(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {item for item in data if isinstance(item, str)}


def save_seen_urls(path: Path, seen_urls: set[str]) -> None:
    path.write_text(json.dumps(sorted(seen_urls), indent=2), encoding="utf-8")


def build_email_body(model_matches: list[Listing], source_url: str) -> str:
    lines = ["Matching Apple Watch listing(s) are now online:", ""]
    for listing in model_matches:
        lines.append(f"- {listing.title}")
        lines.append(f"  {listing.url}")
    lines.extend(["", f"Source: {source_url}"])
    return "\n".join(lines)


def send_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    use_ssl: bool,
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ssl.create_default_context()) as server:
            if smtp_username:
                server.login(smtp_username, smtp_password)
            server.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=ssl.create_default_context())
        if smtp_username:
            server.login(smtp_username, smtp_password)
        server.send_message(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Apple refurbished watch listings and send email notifications.")
    parser.add_argument("--url", default=REFURBISHED_URL, help="Refurbished listing URL")
    parser.add_argument(
        "--model",
        action="append",
        default=None,
        help="Model text to match. Provide multiple times for multiple models.",
    )
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="Path to persisted seen listing URLs")
    parser.add_argument("--dry-run", action="store_true", help="Print matching listings without sending email")

    parser.add_argument("--smtp-host", default=os.getenv("SMTP_HOST", ""))
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv("SMTP_PORT", "587")))
    parser.add_argument("--smtp-username", default=os.getenv("SMTP_USERNAME", ""))
    parser.add_argument("--smtp-password", default=os.getenv("SMTP_PASSWORD", ""))
    parser.add_argument("--smtp-from", default=os.getenv("SMTP_FROM", ""))
    parser.add_argument("--smtp-to", default=os.getenv("SMTP_TO", ""))
    parser.add_argument("--smtp-ssl", action="store_true", default=os.getenv("SMTP_SSL", "").lower() == "true")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    models = args.model if args.model else [DEFAULT_MODEL]

    try:
        page_html = fetch_page(args.url)
    except URLError as err:
        print(f"Failed to fetch listing page: {err}")
        return 1

    listings = parse_watch_listings(page_html)
    matches = filter_listings_by_models(listings, models)

    if not matches:
        print("No configured models found in current listings.")
        return 0

    state_file = Path(args.state_file)
    seen_urls = load_seen_urls(state_file)
    new_matches = [item for item in matches if item.url not in seen_urls]

    if not new_matches:
        print("Configured models exist, but no new listings since the last check.")
        return 0

    body = build_email_body(new_matches, args.url)

    if args.dry_run:
        print(body)
        return 0

    required_fields = {
        "smtp-host": args.smtp_host,
        "smtp-from": args.smtp_from,
        "smtp-to": args.smtp_to,
    }
    missing = [key for key, value in required_fields.items() if not value]
    if missing:
        print(f"Missing required email settings: {', '.join(missing)}")
        return 1

    try:
        send_email(
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_username=args.smtp_username,
            smtp_password=args.smtp_password,
            sender=args.smtp_from,
            recipient=args.smtp_to,
            subject="Apple refurbished watch listing available",
            body=body,
            use_ssl=args.smtp_ssl,
        )
    except (smtplib.SMTPException, OSError) as err:
        print(f"Failed to send email: {err}")
        return 1

    save_seen_urls(state_file, seen_urls | {item.url for item in new_matches})
    print(f"Notification sent for {len(new_matches)} new listing(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
