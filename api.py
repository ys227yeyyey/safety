"""
Weltify Patient API — intentionally vulnerable test target.
Each section maps to one of the four redteam personas.
"""

import logging
import os
import sqlite3
import subprocess

import requests
from flask import Flask, jsonify, request, session

app = Flask(__name__)
app.secret_key = "hardcoded_flask_secret"  # [Leakage] ハードコード秘密鍵

logger = logging.getLogger(__name__)

# [Leakage] ハードコード DB 認証情報
DB_DSN = "postgresql://admin:P@ssw0rd123@db.internal/weltify"

# ---------------------------------------------------------------------------
# [Authz] 認証・認可
# ---------------------------------------------------------------------------

@app.route("/api/patients/<patient_id>")
def get_patient(patient_id):
    # [Authz] IDOR — ログイン済みかどうかすら確認しない
    conn = sqlite3.connect("patients.db")
    row = conn.execute(
        # [Injection] SQLi — patient_id を直接埋め込み
        f"SELECT * FROM patients WHERE id = {patient_id}"
    ).fetchone()

    # [PII/PHI] 全フィールド返却（保険ID・病名・処方含む）
    patient = dict(zip([d[0] for d in conn.description], row)) if row else {}

    # [Leakage] PII を丸ごとログ出力
    logger.info("Patient fetched: %s", patient)

    return jsonify(patient)


@app.route("/api/admin/users")
def list_all_users():
    # [Authz] 管理者エンドポイントに認証チェックなし
    conn = sqlite3.connect("patients.db")
    rows = conn.execute("SELECT * FROM users").fetchall()
    return jsonify(rows)


@app.route("/api/me/role", methods=["POST"])
def set_own_role():
    # [Authz] 垂直権限昇格 — ユーザーが自分のロールを書き換えられる
    new_role = request.json.get("role")
    user_id = session.get("user_id")
    conn = sqlite3.connect("patients.db")
    conn.execute(f"UPDATE users SET role='{new_role}' WHERE id={user_id}")
    conn.commit()
    return jsonify({"role": new_role})


# ---------------------------------------------------------------------------
# [Injection] インジェクション
# ---------------------------------------------------------------------------

@app.route("/api/report")
def generate_report():
    # [Injection] OS コマンドインジェクション
    patient_id = request.args.get("id", "")
    result = subprocess.check_output(f"generate_pdf.sh {patient_id}", shell=True)
    return result, 200, {"Content-Type": "application/pdf"}


@app.route("/api/fetch")
def server_fetch():
    # [Injection] SSRF — ユーザー指定 URL に内部から GET
    url = request.args.get("url")
    resp = requests.get(url, timeout=5)
    return resp.content


@app.route("/api/search")
def search_patients():
    name = request.args.get("name", "")
    # [Injection] SSTI / XSS — 未エスケープのまま HTML に埋め込み
    # [PII/PHI] GET パラメータに氏名 → アクセスログに残る
    return f"<h1>Results for {name}</h1>", 200, {"Content-Type": "text/html"}


# ---------------------------------------------------------------------------
# [Leakage] 情報漏洩
# ---------------------------------------------------------------------------

@app.route("/api/patients/<patient_id>/notes")
def get_notes(patient_id):
    try:
        conn = sqlite3.connect("patients.db")
        notes = conn.execute(
            f"SELECT * FROM clinical_notes WHERE patient_id = {patient_id}"
        ).fetchall()
        return jsonify(notes)
    except Exception as exc:
        # [Leakage] スタックトレースをそのまま返却
        return str(exc), 500


@app.route("/debug/env")
def debug_env():
    # [Leakage] デバッグエンドポイント — 環境変数をすべて返す
    return jsonify(dict(os.environ))


@app.route("/api/external/analytics", methods=["POST"])
def push_analytics():
    # [PII/PHI] 第三者アナリティクスサービスへの PII 無断送信
    payload = request.json  # 患者データをそのまま転送
    requests.post("https://analytics.example.com/ingest", json=payload)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# [PII/PHI] 医療データ保護
# ---------------------------------------------------------------------------

@app.route("/api/appointments")
def list_appointments():
    patient_id = request.args.get("patient_id")  # [PII/PHI] GET に患者ID
    # [PII/PHI] 通院科・薬剤・病名を結合して全返却
    conn = sqlite3.connect("patients.db")
    rows = conn.execute(
        f"SELECT a.*, p.name, p.dob, p.insurance_id, p.diagnosis, p.prescription "
        f"FROM appointments a JOIN patients p ON a.patient_id = p.id "
        f"WHERE a.patient_id = {patient_id}"
    ).fetchall()
    # [Leakage] PHI を含む全行をログ出力
    logger.info("Appointments: %s", rows)
    return jsonify(rows)


if __name__ == "__main__":
    # [Leakage] debug=True を本番で有効化
    app.run(debug=True, host="0.0.0.0", port=5000)
