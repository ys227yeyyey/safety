# Weltify セキュリティ赤チーム Scaffold

PR が作られるたびに Claude Code がセキュリティ研究者として差分をレビューし、脆弱性・PII漏洩を報告する仕組み。

## アーキテクチャ

```
PR 作成
  └─ GitHub Actions (redteam.yml)
       └─ Claude Code Action
            └─ /redteam スキル
                 ├─ git diff を取得
                 ├─ 4ペルソナ × researcher エージェント（並列）
                 │   ├─ PII/PHI 漏洩診断
                 │   ├─ インジェクション脆弱性診断
                 │   ├─ 認証・認可リスク診断
                 │   └─ 情報漏洩・テレメトリ診断
                 ├─ comm.md に結果集約
                 ├─ reports/ にレポート生成
                 └─ PR にコメント投稿（チェックは常に緑）
```

## セットアップ

### 1. GitHub リポジトリの準備

```bash
git remote add origin https://github.com/<org>/<repo>.git
git push -u origin main
```

### 2. Secret の登録

GitHub リポジトリ → Settings → Secrets and variables → Actions → New repository secret

| Name | Value |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code の OAuth トークン |

### 3. 動作確認

PR を作成すると Actions タブに `redteam-on-pr` ワークフローが表示される。
完了後、PR に自動コメントが投稿される。

## ローカルテスト

```bash
cd ~/safety
git init
git checkout -b test-redteam

# わざと脆弱なコードを追加（例）
cat > app.py << 'EOF'
import logging
from flask import request

logger = logging.getLogger(__name__)

def get_patient(patient_id):
    # 脆弱: ユーザー入力を直接クエリに結合
    query = f"SELECT * FROM patients WHERE id = {patient_id}"
    patient = db.execute(query)
    # 脆弱: PII を丸ごとログ出力
    logger.info(f"Patient accessed: {patient}")
    return patient
EOF

git add app.py
git commit -m "test: add vulnerable code for redteam testing"

# /redteam を実行
claude -p "/redteam"
```

`reports/` ディレクトリに `redteam-local-<sha>.md` が生成されれば成功。

## ペルソナのカスタマイズ

`personas/` 以下の `.md` ファイルを編集してペルソナを調整できる。
業界特有のリスク（医療・金融・EC 等）に合わせて観点を追加してください。

## 運用ポリシー

- **Critical 検出でも PR はブロックしない**（人間が読んで判断）
- 誤検知は許容。網羅優先
- 自動修正は行わない（修正は開発者が判断・実施）
- レポートは `reports/` に蓄積され、後からトレンド分析に活用できる
