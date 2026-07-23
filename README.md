# AppleWatch
I am trying to get a refurbished Apple Watch for my mom. This is an automation to notify me when refurbished Apple Watches go on sale.

## Apple refurbished listing checker

Use `/home/runner/work/AppleWatch/AppleWatch/check_apple_watch_listing.py` to check:
- https://www.apple.com/hk/shop/refurbished/watch

The script can notify you by email when selected models appear online. If no model is passed, it defaults to:
- `Apple Watch SE 3 GPS, 40mm`

### Example (dry run)

```bash
python /home/runner/work/AppleWatch/AppleWatch/check_apple_watch_listing.py --dry-run
```

### Configure one or more models

```bash
python /home/runner/work/AppleWatch/AppleWatch/check_apple_watch_listing.py \
  --model "Apple Watch SE 3 GPS, 40mm" \
  --model "Apple Watch Series 10 GPS, 42mm"
```

### Email settings

You can provide SMTP settings either as flags or environment variables:
- `SMTP_HOST` / `--smtp-host`
- `SMTP_PORT` / `--smtp-port` (default `587`)
- `SMTP_USERNAME` / `--smtp-username`
- `SMTP_PASSWORD` / `--smtp-password`
- `SMTP_FROM` / `--smtp-from`
- `SMTP_TO` / `--smtp-to`
- `SMTP_SSL=true` or `--smtp-ssl` for SSL SMTP

Example:

```bash
SMTP_HOST=smtp.example.com \
SMTP_PORT=587 \
SMTP_USERNAME=me@example.com \
SMTP_PASSWORD=app-password \
SMTP_FROM=me@example.com \
SMTP_TO=me@example.com \
python /home/runner/work/AppleWatch/AppleWatch/check_apple_watch_listing.py
```

The script persists seen listing URLs in `.apple_watch_seen.json` and only notifies for newly seen matching listings.
I am trying to get a refurbished Apple Watch for my mom after I got my first pay check from internship. Refurbished Apple Watches are cheaper and they get released on the Apple website spontaneously and I can only purchase them while stocks last.
This is an automation to notify me when refurbished Apple Watches go on sale.
