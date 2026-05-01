# Weltify セキュリティ赤チーム Scaffold

## プロジェクト概要

このリポジトリは Weltify の PR 自動セキュリティレビュー基盤。
医療データ・PII を扱うため、PR 単位でセキュリティ研究者視点のコードレビューを自動実行する。

## 運用ルール（絶対ルール）

1. `/redteam` 実行は常に **exit 0**（Critical 検出でも PR をブロックしない・緩め運用）
2. マルチエージェントは **researcher 4並列のみ**。implementer 起動禁止
3. エージェント間通信は **agent-log スキル → comm.md** 経由のみ。直接コンテキスト共有禁止
4. researcher は **Read/Grep のみ**。Edit/Write/Bash 禁止（診断専任・修正禁止）
5. 出力レポートは `reports/redteam-<PR番号>-<short-sha>.md`

## スコープ

- 自動修正・PR への自動 push: **禁止**
- Critical 検出での PR ブロック: **禁止**（将来オプトインで追加可能）
- 外部ツール連携（Snyk/Semgrep 等）: スコープ外
- Slack/メール通知: スコープ外

## ディレクトリ構成

```
.claude/skills/redteam/SKILL.md  # /redteam コマンド本体
.claude/settings.json            # ツール allowlist
.github/workflows/redteam.yml    # GitHub Actions
personas/                        # セキュリティ研究者ペルソナ（researcher に渡す）
reports/                         # 生成レポート置き場
comm.md                          # エージェント間通信（agent-log が管理）
```

## GitHub Actions セットアップ

1. GitHub リポジトリ Settings → Secrets に `CLAUDE_CODE_OAUTH_TOKEN` を登録
2. PR を作成すると自動的にレッドチームレビューが走る
3. レビュー結果は PR コメントに投稿される（チェックは常に緑）
