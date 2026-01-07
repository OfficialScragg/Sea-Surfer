# Sea Surfer

A stealthy CSRF payload hosting tool with authenticated dev portal.

## Features

- **Stealthy**: Unknown routes redirect to a configurable decoy URL (e.g., Google)
- **Secure Credentials**: Set in config, automatically removed after startup
- **Create Payloads**: Add custom HTML/JS content for CSRF testing
- **Unique URLs**: Each payload gets a unique URL slug (`/p/your-slug`)
- **Auto-Submit**: Automatically submit forms when payload page loads
- **Hidden Mode**: Make payload content invisible to victims

## Quick Start

1. Add credentials to `config.json`:

```json
{
  "decoy_url": "https://google.com",
  "dev_path": "/dev",
  "username": "admin",
  "password": "your-secret-password"
}
```

2. Run the server:

```bash
pip install -r requirements.txt
python3 app.py
```

3. Credentials are automatically removed from config and hashed in `.credentials`

## Stealth Behavior

All admin routes are prefixed with `dev_path` (default: `/dev`), making them hard to discover:

| Route | Behavior |
|-------|----------|
| `/` | Redirect to decoy URL |
| `{dev_path}/login` | Login page |
| `{dev_path}` | Dev portal (requires auth) |
| `{dev_path}/create` | Create payload (requires auth) |
| `{dev_path}/edit/<slug>` | Edit payload (requires auth) |
| `{dev_path}/logout` | Logout |
| `/p/<slug>` | Serve payload (no auth) |
| `/p/<invalid>` | Redirect to decoy URL |
| Any other route | Redirect to decoy URL |

Wrong credentials also redirect to decoy (no error shown).

**Anti-fuzzing**: Change `dev_path` to something obscure like `/x7k9m2` to prevent discovery.

## Configuration

Edit `config.json`:

```json
{
  "decoy_url": "https://google.com",
  "dev_path": "/dev",
  "username": "admin",
  "password": "changeme"
}
```

After first run, credentials are removed and only these remain:
```json
{
  "decoy_url": "https://google.com",
  "dev_path": "/dev"
}
```

Hashed credentials are stored in `.credentials` (auto-generated).

## Usage

1. Add credentials to `config.json`
2. Start the server: `python3 app.py`
3. Go to `{dev_path}/login` (e.g., `/dev/login`) and authenticate
4. Create payloads in the dev portal
5. Share payload URLs: `http://yourserver.com/p/my-payload`

To change credentials: delete `.credentials` and add new ones to `config.json`.

## Example Payload

```html
<form action="https://target.com/api/delete" method="POST">
  <input type="hidden" name="id" value="123">
</form>
```

With auto-submit enabled, this form will automatically POST to the target.

## Files

```
├── app.py           # Flask application
├── config.json      # Stealth configuration
├── .credentials     # Hashed credentials (auto-generated)
├── payloads.json    # Stored payloads (auto-created)
├── requirements.txt
└── templates/
    ├── base.html
    ├── create.html
    ├── index.html
    ├── login.html
    └── payload.html
```

## Disclaimer

This tool is for authorized security testing only. Always obtain proper permission before testing.
