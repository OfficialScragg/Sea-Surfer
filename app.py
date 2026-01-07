from flask import Flask, render_template, request, redirect, url_for, abort, session
from functools import wraps
import json
import os
import secrets
import sys
import hashlib

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DATA_FILE = "payloads.json"
CONFIG_FILE = "config.json"
CREDS_FILE = ".credentials"

# Auth credentials (loaded on startup)
AUTH_USER = None
AUTH_PASS_HASH = None

# Dev path prefix (loaded on startup)
DEV_PATH = None


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"decoy_url": "https://google.com", "dev_path": "/dev"}


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_credentials():
    """Load credentials - from config (first run) or .credentials file (restarts)."""
    global AUTH_USER, AUTH_PASS_HASH, DEV_PATH
    
    config = load_config()
    DEV_PATH = config.get("dev_path", "/dev").rstrip("/")
    
    # Check if hashed credentials already exist
    if os.path.exists(CREDS_FILE):
        with open(CREDS_FILE, "r") as f:
            data = json.load(f)
            AUTH_USER = data["username"]
            AUTH_PASS_HASH = data["password_hash"]
        print(f"[*] Credentials loaded for user: {AUTH_USER}")
        return
    
    # First run - load from config and clear
    if "username" not in config or "password" not in config:
        print("[!] ERROR: No credentials found in config.json")
        print("[!] Add 'username' and 'password' fields to config.json and restart")
        sys.exit(1)
    
    AUTH_USER = config["username"]
    AUTH_PASS_HASH = hash_password(config["password"])
    
    # Save hashed credentials to hidden file
    with open(CREDS_FILE, "w") as f:
        json.dump({"username": AUTH_USER, "password_hash": AUTH_PASS_HASH}, f)
    
    # Remove plaintext credentials from config
    del config["username"]
    del config["password"]
    save_config(config)
    
    print(f"[*] Credentials loaded for user: {AUTH_USER}")
    print("[*] Plaintext credentials removed from config.json")


def load_payloads():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}


def save_payloads(payloads):
    with open(DATA_FILE, "w") as f:
        json.dump(payloads, f, indent=2)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            config = load_config()
            return redirect(config["decoy_url"])
        return f(*args, **kwargs)
    return decorated


def register_routes(app, dev_path):
    """Register all routes with the configured dev_path prefix."""
    
    # === Auth Routes ===
    
    @app.route(f"{dev_path}/login", methods=["GET", "POST"])
    def login():
        config = load_config()
        
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            
            if username == AUTH_USER and hash_password(password) == AUTH_PASS_HASH:
                session["authenticated"] = True
                session.permanent = True
                return redirect(dev_path)
            
            # Wrong creds = redirect to decoy (stealth)
            return redirect(config["decoy_url"])
        
        return render_template("login.html")
    
    
    @app.route(f"{dev_path}/logout")
    def logout():
        session.clear()
        config = load_config()
        return redirect(config["decoy_url"])
    
    
    # === Dev Portal Routes ===
    
    @app.route(dev_path)
    @login_required
    def index():
        payloads = load_payloads()
        return render_template("index.html", payloads=payloads, dev_path=dev_path)
    
    
    @app.route(f"{dev_path}/create", methods=["GET", "POST"])
    @login_required
    def create():
        if request.method == "POST":
            slug = request.form.get("slug", "").strip()
            name = request.form.get("name", "").strip()
            content = request.form.get("content", "")
            auto_submit = request.form.get("auto_submit") == "on"
            hide_form = request.form.get("hide_form") == "on"

            if not slug or not name:
                return render_template("create.html", error="Slug and name are required", dev_path=dev_path)

            payloads = load_payloads()
            payloads[slug] = {
                "name": name,
                "content": content,
                "auto_submit": auto_submit,
                "hide_form": hide_form,
            }
            save_payloads(payloads)
            return redirect(dev_path)

        return render_template("create.html", dev_path=dev_path)
    
    
    @app.route(f"{dev_path}/edit/<slug>", methods=["GET", "POST"])
    @login_required
    def edit(slug):
        payloads = load_payloads()
        if slug not in payloads:
            abort(404)

        if request.method == "POST":
            new_slug = request.form.get("slug", "").strip()
            name = request.form.get("name", "").strip()
            content = request.form.get("content", "")
            auto_submit = request.form.get("auto_submit") == "on"
            hide_form = request.form.get("hide_form") == "on"

            if not new_slug or not name:
                return render_template(
                    "create.html", error="Slug and name are required", 
                    payload=payloads[slug], slug=slug, dev_path=dev_path
                )

            if new_slug != slug:
                del payloads[slug]

            payloads[new_slug] = {
                "name": name,
                "content": content,
                "auto_submit": auto_submit,
                "hide_form": hide_form,
            }
            save_payloads(payloads)
            return redirect(dev_path)

        return render_template("create.html", payload=payloads[slug], slug=slug, dev_path=dev_path)
    
    
    @app.route(f"{dev_path}/delete/<slug>", methods=["POST"])
    @login_required
    def delete(slug):
        payloads = load_payloads()
        if slug in payloads:
            del payloads[slug]
            save_payloads(payloads)
        return redirect(dev_path)


# === Payload Routes (always at /p/) ===

@app.route("/p/<slug>")
def payload(slug):
    payloads = load_payloads()
    if slug not in payloads:
        config = load_config()
        return redirect(config["decoy_url"])
    return render_template("payload.html", payload=payloads[slug])


# === Catch-all: Redirect unknown routes to decoy ===

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    config = load_config()
    return redirect(config["decoy_url"])


if __name__ == "__main__":
    load_credentials()
    register_routes(app, DEV_PATH)
    
    print(f"[*] Dev portal: http://127.0.0.1:5000{DEV_PATH}/login")
    print(f"[*] Payloads served at: /p/<slug>")
    print(f"[*] All other routes redirect to decoy URL")
    
    app.run(debug=True, port=5000)
