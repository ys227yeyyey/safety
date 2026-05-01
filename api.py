"""
Weltify 患者データ API（テスト用）
"""
import sqlite3
import subprocess
import logging
import os
import requests
from flask import Flask, request, jsonify
import jwt

app = Flask(__name__)

# ハードコードされた認証情報
DB_PASSWORD = "admin1234"
JWT_SECRET = "supersecret"
SENTRY_DSN = "https://abc123@sentry.io/999"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- 認証ヘルパー ---

def get_current_user(token):
    # alg: none 攻撃が可能・有効期限チェックなし
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256", "none"])
    return payload


# --- エンドポイント ---

@app.route("/patients/<int:patient_id>", methods=["GET"])
def get_patient(patient_id):
    """IDOR: patient_id の所有権チェックなし"""
    token = request.headers.get("Authorization", "")
    user = get_current_user(token)
    logger.info(f"User fetched patient: {user}")  # オブジェクト丸ごとログ出力

    conn = sqlite3.connect("weltify.db")
    # SQL インジェクション: ユーザー入力を直接クエリに結合
    name_filter = request.args.get("name", "")
    query = f"SELECT * FROM patients WHERE id = {patient_id} AND name LIKE '%{name_filter}%'"
    cur = conn.execute(query)
    row = cur.fetchone()

    if row is None:
        return jsonify({"error": "not found"}), 404

    # PHI を全フィールド返却（過剰露出）
    patient = {
        "id": row[0],
        "name": row[1],
        "dob": row[2],
        "insurance_id": row[3],
        "diagnosis": row[4],
        "prescription": row[5],
        "visit_history": row[6],
    }
    return jsonify(patient)


@app.route("/export", methods=["GET"])
def export_report():
    """OS コマンドインジェクション"""
    report_type = request.args.get("type", "pdf")
    # ユーザー入力をコマンドに直接渡す
    result = subprocess.check_output(f"generate_report --format {report_type}", shell=True)
    return result


@app.route("/fetch-external", methods=["POST"])
def fetch_external():
    """SSRF: ユーザー指定 URL へ内部から直接リクエスト"""
    url = request.json.get("url")
    resp = requests.get(url, timeout=5)
    return jsonify({"body": resp.text})


@app.route("/admin/users", methods=["GET"])
def admin_users():
    """認証チェックなし管理者エンドポイント"""
    conn = sqlite3.connect("weltify.db")
    rows = conn.execute("SELECT * FROM users").fetchall()
    return jsonify(rows)


@app.route("/debug", methods=["GET"])
def debug_info():
    """デバッグエンドポイントが本番に残留"""
    return jsonify({
        "env": dict(os.environ),
        "db_password": DB_PASSWORD,
    })


@app.route("/search", methods=["GET"])
def search_patient():
    """GET パラメータに PII 混入（アクセスログに患者名が残る）"""
    # 例: /search?patient_name=山田太郎&dob=1980-01-01
    patient_name = request.args.get("patient_name")
    dob = request.args.get("dob")
    conn = sqlite3.connect("weltify.db")
    cur = conn.execute(
        "SELECT * FROM patients WHERE name = ? AND dob = ?", (patient_name, dob)
    )
    rows = cur.fetchall()
    return jsonify(rows)


@app.errorhandler(Exception)
def handle_error(e):
    """スタックトレースをそのまま API レスポンスに返す"""
    import traceback
    return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


if __name__ == "__main__":
    app.run(debug=True)
