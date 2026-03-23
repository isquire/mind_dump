# Mind Dump

A self-hosted productivity and planning web app built for neurodivergent users
(particularly people with ADHD). Designed to reduce friction, minimise
overwhelm, and support focus.

**Stack:** Python 3 + Flask · SQLite via SQLAlchemy · Bootstrap 5 (local) ·
Quill.js rich-text editor (local)

---

> ⚠️ **Security notice:** This app is designed for single-user, self-hosted
> LAN use only. **Do not expose it to the internet** without placing it behind
> a reverse proxy (e.g. nginx or Caddy) with HTTPS and a firewall. There is no
> rate limiting, no HTTPS, and no multi-user access control.

---

## Features

- **Quick Capture** — one text field, one button, zero required fields
- **My One Thing** — pin a single task as today's focus, shown prominently
- **Dashboard** — today, this week, overdue (amber not red), weekly progress
- **Focus Mode** — full-screen, no navigation, completion animation
- **Mind Dump** — capture everything, triage later (promote to Task/Project/Idea)
- **Big Ideas → Projects → Tasks** hierarchy with progress bars
- **Quill rich-text** notes on tasks
- **CSRF protection** on all forms via Flask-WTF
- **bcrypt** password hashing, session timeout after 60 min inactivity
- All assets served locally — no runtime internet dependencies

---

## Installation on Debian 12

### 1. Install system dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git
```

### 2. Clone and set up

```bash
git clone <your-repo-url> mind_dump
cd mind_dump
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Download vendor assets (Bootstrap, Quill)

This only needs to run once. It downloads all frontend assets locally so
the app has no runtime internet dependencies.

```bash
bash setup_assets.sh
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set a strong `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# Paste the output into .env as SECRET_KEY=...
```

### 5. Start the app

```bash
bash run.sh
```

On first run you will be prompted to create your username and password.
The app will then be available at `http://<your-server-ip>:5000`.

---

## Running as a systemd service (optional)

Create `/etc/systemd/system/mind_dump.service`:

```ini
[Unit]
Description=Mind Dump productivity app
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/mind_dump
EnvironmentFile=/home/<your-user>/mind_dump/.env
Environment=FLASK_ENV=production
Environment=FLASK_DEBUG=0
ExecStart=/home/<your-user>/mind_dump/venv/bin/python app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mind_dump
```

---

## Directory structure

```
mind_dump/
├── app.py              # App factory, security headers, session timeout
├── models.py           # SQLAlchemy ORM models
├── forms/              # Flask-WTF form classes
├── routes/             # Flask Blueprints (auth, dashboard, focus, …)
├── templates/          # Jinja2 HTML templates
├── static/
│   ├── css/app.css     # Custom styles
│   ├── js/app.js       # Confirm dialogs, tooltips
│   └── vendor/         # Bootstrap, Bootstrap Icons, Quill (local)
├── requirements.txt
├── run.sh              # Production startup script
├── setup_assets.sh     # One-time vendor asset downloader
└── .env.example
```

---

## Security design

| Concern | Approach |
|---------|---------|
| Passwords | bcrypt hashed, never stored plain |
| Sessions | Flask-Login, 60 min inactivity timeout |
| CSRF | Flask-WTF on every form |
| SQL injection | SQLAlchemy ORM only, no string concatenation |
| XSS in notes | bleach sanitisation of Quill HTML output |
| URL validation | http:// / https:// prefix enforced on external_link |
| Clickjacking | `X-Frame-Options: DENY` header |
| Secret key | Loaded from `SECRET_KEY` env var, never hardcoded |
| Debug mode | `debug=False` enforced; `run.sh` sets `FLASK_ENV=production` |

---

## Updating

```bash
cd mind_dump
git pull
source venv/bin/activate
pip install -r requirements.txt
# Database migrations are automatic (SQLAlchemy create_all)
bash run.sh
```
