import logging
import sqlite3
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)
logger = logging.getLogger(__name__)

# [Leakage] ハードコード認証情報
DB_PASSWORD = "P@ssw0rd!2024"
API_SECRET = "sk-live-abc123xyz"

# [PII/PHI] 患者データをGETパラメータで受け取り、丸ごとログ出力
@app.route("/patient/search")
def search_patient():
    name = request.args.get("name")       # URLに氏名が露出
    dob  = request.args.get("dob")        # URLに生年月日が露出
    logger.info(f"Searching patient: name={name}, dob={dob}")  # PII をログ出力

    # [Injection] SQLインジェクション
    query = f"SELECT * FROM patients WHERE name = '{name}' AND dob = '{dob}'"
    conn = sqlite3.connect("patients.db")
    rows = conn.execute(query).fetchall()

    # [PII/PHI] 全カラム（診断名・保険IDも含む）をそのまま返却
    return jsonify(rows)

# [Authz] IDOR: 認可チェックなしで任意の患者レコードを取得
@app.route("/patient/<int:patient_id>")
def get_patient(patient_id):
    conn = sqlite3.connect("patients.db")
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    return jsonify(row)

# [Injection] OSコマンドインジェクション
@app.route("/report/export")
def export_report():
    fmt = request.args.get("format", "pdf")
    subprocess.call(f"generate_report --format {fmt}", shell=True)
    return "exported"

# [Injection] XSS: 未エスケープでHTMLに出力
@app.route("/greet")
def greet():
    user = request.args.get("user", "")
    return f"<h1>Welcome, {user}</h1>"

# [Authz] 管理者エンドポイントに認証なし
@app.route("/admin/users")
def list_all_users():
    conn = sqlite3.connect("patients.db")
    rows = conn.execute("SELECT * FROM users").fetchall()
    return jsonify(rows)

# [Leakage] デバッグエンドポイントが本番に残留
@app.route("/debug/env")
def debug_env():
    import os
    return jsonify(dict(os.environ))

# [Leakage] スタックトレースをそのままレスポンスに返却
@app.route("/record/<int:record_id>/delete", methods=["POST"])
def delete_record(record_id):
    try:
        conn = sqlite3.connect("patients.db")
        conn.execute(f"DELETE FROM records WHERE id = {record_id}")
        conn.commit()
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(debug=True)  # [Leakage] debug=True が本番で有効
