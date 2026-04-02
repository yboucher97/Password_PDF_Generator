# Password PDF Generator

WiFi/password PDF webhook service for Ubuntu or Debian.

This repo now installs into one fixed service root:

```text
/opt/services/password-pdf-generator/
```

The goal is a layout that stays the same no matter where you run install or update commands.

## Installed Layout

After install, the important paths are:

```text
/opt/services/password-pdf-generator/
/opt/services/password-pdf-generator/app/
/opt/services/password-pdf-generator/.venv/
/opt/services/password-pdf-generator/config/
/opt/services/password-pdf-generator/config/brand_settings.json
/opt/services/password-pdf-generator/config/password-pdf-generator.env
/opt/services/password-pdf-generator/data/
/opt/services/password-pdf-generator/logs/
/etc/systemd/system/password-pdf-generator.service
/etc/caddy/conf.d/webhooks.caddy
```

The PDF app keeps its own code, venv, config, data, and logs together under one folder.

## Install

Run this on the target machine:

```bash
sudo bash <(curl -fsSL https://raw.githubusercontent.com/yboucher97/Password_PDF_Generator/main/install.sh)
```

The installer:

- installs system packages
- clones or updates the repo into `/opt/services/password-pdf-generator/app`
- creates `/opt/services/password-pdf-generator/.venv`
- stores config in `/opt/services/password-pdf-generator/config`
- stores generated files in `/opt/services/password-pdf-generator/data`
- stores logs in `/opt/services/password-pdf-generator/logs`
- creates `password-pdf-generator.service`
- writes the shared Caddy file at `/etc/caddy/conf.d/webhooks.caddy`

## Update

On the target machine:

```bash
sudo /opt/services/password-pdf-generator/app/update.sh
```

That keeps the same paths, refreshes the repo, rebuilds the venv, reapplies the service config, and rewrites the shared Caddy file.

## Shared Caddy Layout

This installer now assumes the PDF webhook and the quote geolocation webhook live on the same VM and same hostname.

The shared Caddy file routes:

- `/pdf/*` to the PDF service on `127.0.0.1:8000`
- `/quote-geolocation/*` to the quote geolocation service on `127.0.0.1:8050`
- everything else to the PDF service for backward compatibility

So the preferred public paths are:

- PDF health: `https://pdf.wifiplex.ca/pdf/health`
- PDF webhook: `https://pdf.wifiplex.ca/pdf/webhooks/zoho/wifi-pdfs`

The older direct PDF paths still work because Caddy falls back to the PDF service.

## Runtime

Local service:

- app module: `wifi_pdf.api:app`
- local health: `http://127.0.0.1:8000/health`
- local webhook: `http://127.0.0.1:8000/webhooks/zoho/wifi-pdfs`

Public paths through the shared Caddy site:

- `GET /pdf/health`
- `POST /pdf/webhooks/zoho/wifi-pdfs`

## Key Installer Variables

- `PASSWORD_PDF_HOST`
- `PASSWORD_PDF_API_KEY`
- `PASSWORD_PDF_ENABLE_WORKDRIVE`
- `PASSWORD_PDF_ZOHO_REGION`
- `PASSWORD_PDF_PORT`
- `PASSWORD_PDF_QUOTE_GEO_PORT`
- `ZOHO_WORKDRIVE_CLIENT_ID`
- `ZOHO_WORKDRIVE_CLIENT_SECRET`
- `ZOHO_WORKDRIVE_REFRESH_TOKEN`
- `ZOHO_WORKDRIVE_PARENT_FOLDER_ID`

## Logs And Data

- PDFs, manifests, exports, and jobs are written under:
  `/opt/services/password-pdf-generator/data/output/pdf/wifi`
- logs are written under:
  `/opt/services/password-pdf-generator/logs`
- main rotating log file:
  `/opt/services/password-pdf-generator/logs/wifi_pdf.log`

## Docs

- app details: [wifi_pdf/README.md](./wifi_pdf/README.md)
- deployment notes: [docs/wifi-pdf-ubuntu-esxi.md](./docs/wifi-pdf-ubuntu-esxi.md)
