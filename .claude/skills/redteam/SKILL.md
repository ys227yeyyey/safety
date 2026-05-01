---
name: redteam
description: PR差分をセキュリティ研究者視点で4並列レビューし、脆弱性・PII漏洩を洗い出してPRコメントに報告する
allowed-tools: [Bash, Read, Grep, Glob, Write, Agent]
---

# /redteam — PR セキュリティ自動レッドチーム

このスキルが起動されたら、以下のステップを順番に実行する。

## B1: 差分取得

```bash
git diff origin/main...HEAD > /tmp/diff.patch
```

差分が空の場合は "差分なし" レポートを生成して B6 へスキップ。

PR番号とコミットSHAを取得:
```bash
PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null || echo "local")
SHORT_SHA=$(git rev-parse --short HEAD)
```

## B2: ペルソナファイルの確認

以下4ファイルを Read する（プロジェクトルートからの相対パス）:
- `personas/pii-phi.md`
- `personas/injection.md`
- `personas/authz.md`
- `personas/leakage.md`

## B3: 4ペルソナ並列起動

**1メッセージで4つの Agent tool call を同時に送る**（sequential 禁止）。
各エージェントの設定:
- `subagent_type`: `researcher`
- 使用ツール: Read, Grep のみ（Edit/Write 禁止）

各エージェントへのプロンプトテンプレート（ペルソナごとにファイルパスを変える）:

```
あなたは <ペルソナファイル名> に記述されたセキュリティ研究者です。
差分ファイル /tmp/diff.patch を Read して診断してください。

診断後、agent-log スキルを使って comm.md に以下の書式で追記してください:

## [<ペルソナ名>] 所見

| Severity | リスク概要 | 該当箇所 | 推奨対策 |
|---|---|---|---|
| Critical/High/Medium/Low/Info | ... | ファイル:行 | ... |

所見がない場合は「該当なし」と記載してください。
誤検知でも構いません。網羅優先でお願いします。
```

## B4: comm.md 待機・読み出し

4エージェントの完了を待ってから `comm.md` を Read する。

## B5: 集約・重複排除・Severity ソート

comm.md の内容を以下の順でソートして集約:
1. Critical
2. High
3. Medium
4. Low
5. Info
6. 該当なし

重複エントリは統合する。

## B6: レポート生成

`reports/redteam-<PR番号>-<short-sha>.md` に Write する。

レポートフォーマット:
```markdown
# Redteam Report — PR #<番号> (<short-sha>)

**実行日時**: <ISO8601>
**対象差分**: <変更ファイル数> files changed

## サマリー

| Severity | 件数 |
|---|---|
| Critical | N |
| High | N |
| Medium | N |
| Low | N |
| Info | N |

## 詳細所見

<集約済み所見テーブル>

---
*このレポートは Claude Code による自動生成です。マージ可否は人間が判断してください。*
```

## B7: PRコメント投稿

```bash
gh pr comment <PR番号> --body-file reports/redteam-<PR番号>-<short-sha>.md
```

PR番号が "local" の場合はコメント投稿をスキップし、レポートパスをコンソール出力する。

## B8: 正常終了

**Critical 検出でも exit 0**。PR ブロックは行わない（緩め運用）。
チェックステータスは常に success のまま。
