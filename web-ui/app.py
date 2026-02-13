import base64
import json
import os
import secrets
import tempfile
import uuid

from flask import Flask, flash, redirect, render_template, request, url_for
import docker

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))

CONFIG_FILE = os.environ.get("CONFIG_FILE", "/app/config.json")
XRAY_CONTAINER_NAME = os.environ.get("XRAY_CONTAINER_NAME", "xray-reality")
SERVER_NAME = os.environ.get("SERVER_NAME", "your-domain.com")
PUBLIC_KEY = os.environ.get("PUBLIC_KEY", "your-public-key")
SNI = os.environ.get("SNI", "www.microsoft.com")
PORT = os.environ.get("PORT", "443")
FP = os.environ.get("FP", "chrome")
UI_USERNAME = os.environ.get("UI_USERNAME", "admin")
UI_PASSWORD = os.environ.get("UI_PASSWORD", "change-me")


def require_basic_auth():
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        return False
    payload = auth.split(" ", 1)[1]
    try:
        decoded = base64.b64decode(payload).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    if ":" not in decoded:
        return False
    username, password = decoded.split(":", 1)
    return secrets.compare_digest(username, UI_USERNAME) and secrets.compare_digest(
        password, UI_PASSWORD
    )


@app.before_request
def enforce_basic_auth():
    if request.endpoint in {"health"}:
        return None
    if require_basic_auth():
        return None
    return (
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Xray UI"'},
    )


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_config(config):
    directory = os.path.dirname(CONFIG_FILE) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=directory, encoding="utf-8") as tmp:
        json.dump(config, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
    os.replace(tmp.name, CONFIG_FILE)


def get_vless_inbound(config):
    for inbound in config.get("inbounds", []):
        if inbound.get("protocol") != "vless":
            continue
        settings = inbound.get("settings", {})
        if settings.get("clients") is not None:
            return inbound
    return None


def restart_xray():
    if os.environ.get("XRAY_RESTART", "true").lower() in {"false", "0", "no"}:
        return
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    container = client.containers.get(XRAY_CONTAINER_NAME)
    container.restart()


def resolve_link_settings(config, inbound):
    resolved_sni = SNI
    if not resolved_sni or resolved_sni == "www.microsoft.com":
        reality = inbound.get("streamSettings", {}).get("realitySettings", {})
        server_names = reality.get("serverNames") or []
        if server_names:
            resolved_sni = server_names[0]

    resolved_port = PORT
    if not resolved_port or resolved_port == "443":
        inbound_port = inbound.get("port")
        if inbound_port:
            resolved_port = str(inbound_port)

    return resolved_sni, resolved_port


def build_link(client_id, short_id, name, sni, port, fingerprint):
    return (
        f"vless://{client_id}@{SERVER_NAME}:{port}?type=tcp&security=reality"
        f"&pbk={PUBLIC_KEY}&fp={fingerprint}&sni={sni}&sid={short_id}&spx=%2F"
        f"&flow=xtls-rprx-vision#{name}"
    )


@app.route("/health")
def health():
    return "ok", 200


@app.route("/")
def index():
    config = load_config()
    inbound = get_vless_inbound(config)
    if not inbound:
        return "VLESS inbound not found", 500
    settings = inbound.get("settings", {})
    clients = settings.get("clients", [])
    disabled = set(settings.get("disabledClients", []) or [])
    clients_view = []
    for client in clients:
        name = client.get("email", "")
        clients_view.append(
            {
                "id": client.get("id"),
                "name": name,
                "flow": client.get("flow"),
                "level": client.get("level"),
                "disabled": name in disabled,
            }
        )
    return render_template(
        "index.html",
        clients=clients_view,
        disabled=sorted(disabled),
        server_name=SERVER_NAME,
    )


@app.route("/add", methods=["POST"])
def add_client():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Укажите имя пользователя.", "error")
        return redirect(url_for("index"))
    config = load_config()
    inbound = get_vless_inbound(config)
    if not inbound:
        flash("VLESS inbound не найден.", "error")
        return redirect(url_for("index"))
    settings = inbound.setdefault("settings", {})
    clients = settings.setdefault("clients", [])
    if any(client.get("email") == name for client in clients):
        flash("Пользователь с таким именем уже существует.", "error")
        return redirect(url_for("index"))

    client_id = str(uuid.uuid4())
    reality = inbound.setdefault("streamSettings", {}).setdefault("realitySettings", {})
    short_ids = reality.setdefault("shortIds", [])
    if short_ids:
        short_id = secrets.choice(short_ids)
    else:
        short_id = secrets.token_hex(3)
        short_ids.append(short_id)
    clients.append({"id": client_id, "flow": "xtls-rprx-vision", "email": name})

    save_config(config)
    try:
        restart_xray()
        flash("Пользователь добавлен и Xray перезапущен.", "success")
    except docker.errors.DockerException as exc:
        flash(f"Пользователь добавлен, но перезапуск Xray не удался: {exc}", "error")

    resolved_sni, resolved_port = resolve_link_settings(config, inbound)
    if PUBLIC_KEY == "your-public-key":
        flash("Задайте PUBLIC_KEY для генерации ссылки.", "error")
        return redirect(url_for("index"))
    link = build_link(client_id, short_id, name, resolved_sni, resolved_port, FP)
    flash(f"Ссылка клиента: {link}", "info")
    return redirect(url_for("index"))


@app.route("/remove", methods=["POST"])
def remove_client():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Укажите имя пользователя для удаления.", "error")
        return redirect(url_for("index"))
    config = load_config()
    inbound = get_vless_inbound(config)
    if not inbound:
        flash("VLESS inbound не найден.", "error")
        return redirect(url_for("index"))
    settings = inbound.setdefault("settings", {})
    clients = settings.setdefault("clients", [])
    original_count = len(clients)
    clients[:] = [client for client in clients if client.get("email") != name]
    if len(clients) == original_count:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("index"))

    save_config(config)
    try:
        restart_xray()
        flash("Пользователь удален, Xray перезапущен.", "success")
    except docker.errors.DockerException as exc:
        flash(f"Пользователь удален, но перезапуск Xray не удался: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/disable", methods=["POST"])
def disable_client():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Укажите имя пользователя для отключения.", "error")
        return redirect(url_for("index"))
    config = load_config()
    inbound = get_vless_inbound(config)
    if not inbound:
        flash("VLESS inbound не найден.", "error")
        return redirect(url_for("index"))
    settings = inbound.setdefault("settings", {})
    disabled = settings.setdefault("disabledClients", [])
    if name not in disabled:
        disabled.append(name)
    save_config(config)
    try:
        restart_xray()
        flash("Пользователь отключен, Xray перезапущен.", "success")
    except docker.errors.DockerException as exc:
        flash(f"Пользователь отключен, но перезапуск Xray не удался: {exc}", "error")
    return redirect(url_for("index"))


@app.route("/enable", methods=["POST"])
def enable_client():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Укажите имя пользователя для включения.", "error")
        return redirect(url_for("index"))
    config = load_config()
    inbound = get_vless_inbound(config)
    if not inbound:
        flash("VLESS inbound не найден.", "error")
        return redirect(url_for("index"))
    settings = inbound.setdefault("settings", {})
    disabled = settings.setdefault("disabledClients", [])
    settings["disabledClients"] = [entry for entry in disabled if entry != name]
    save_config(config)
    try:
        restart_xray()
        flash("Пользователь включен, Xray перезапущен.", "success")
    except docker.errors.DockerException as exc:
        flash(f"Пользователь включен, но перезапуск Xray не удался: {exc}", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
