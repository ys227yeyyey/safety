"""
aa.py — Weltify 医療記録 API（テスト用ダミーファイル）
/redteam ペルソナ検証用に意図的な脆弱性を含む
"""

import sqlite3
import subprocess
import logging
import traceback
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- 脆弱: ハードコードされた認証情報 ---
DB_PASSWORD = "admin123"
SECRET_KEY   = "hardcoded-jwt-secret-do-not-use"
SENTRY_DSN   = "https://abcdef1234567890@sentry.io/123456"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def get_db():
    conn = sqlite3.connect("patients.db")
    return conn


# ============================================================
# 1. SQL インジェクション — ユーザー入力を直接クエリに結合
# ============================================================
@app.route("/patients/search")
def search_patients():
    name = request.args.get("name", "")
    conn = get_db()
    cur = conn.cursor()
    # 脆弱: f-string で直接結合
    query = f"SELECT * FROM patients WHERE name = '{name}'"
    cur.execute(query)
    rows = cur.fetchall()
    return jsonify(rows)


# ============================================================
# 2. IDOR — patient_id の所有者チェックなし
# ============================================================
@app.route("/patients/<int:patient_id>/records")
def get_records(patient_id):
    # 脆弱: ログインユーザーと patient_id の紐付け検証なし
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM medical_records WHERE patient_id = ?", (patient_id,))
    records = cur.fetchall()
    return jsonify(records)


# ============================================================
# 3. PII/PHI ログ & レスポンス過剰露出
# ============================================================
@app.route("/patients/<int:patient_id>")
def get_patient(patient_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
    patient = cur.fetchone()

    # 脆弱: PHI をそのままログ出力
    logger.debug("Patient fetched: %s", patient)

    # 脆弱: 診断名・保険ID など全フィールドを返す
    return jsonify({
        "id": patient[0],
        "name": patient[1],
        "dob": patient[2],
        "insurance_id": patient[3],
        "diagnosis": patient[4],
        "medication": patient[5],
    })


# ============================================================
# 4. OS コマンドインジェクション
# ============================================================
@app.route("/export")
def export_report():
    fmt = request.args.get("format", "pdf")
    # 脆弱: ユーザー入力を shell=True で渡す
    result = subprocess.run(
        f"generate_report --format {fmt}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return jsonify({"output": result.stdout})


# ============================================================
# 5. スタックトレースの外部返却 & デバッグエンドポイント
# ============================================================
@app.errorhandler(Exception)
def handle_error(e):
    # 脆弱: 詳細なスタックトレースを API レスポンスとして返す
    return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/debug/db")
def debug_db():
    # 脆弱: 認証なしのデバッグエンドポイント — 本番環境に残存
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    return jsonify({"tables": tables, "db_password": DB_PASSWORD})


# ============================================================
# 6. 権限チェックなし管理エンドポイント
# ============================================================
@app.route("/admin/users", methods=["GET", "DELETE"])
def admin_users():
    # 脆弱: ロール検証なし — 一般ユーザーでも叩ける
    user_id = request.args.get("id")
    conn = get_db()
    cur = conn.cursor()
    if request.method == "DELETE":
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return jsonify({"deleted": user_id})
    cur.execute("SELECT id, name, email, role, password_hash FROM users")
    return jsonify(cur.fetchall())


if __name__ == "__main__":
    # 脆弱: debug=True を本番で有効化
    app.run(debug=True, host="0.0.0.0", port=5000)
