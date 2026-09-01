# AIエージェントセキュリティとローカルサンドボックス化ガイド

## 1. 背景と概要

2026年に入り、**正規の社内AIエージェントや開発環境に組み込まれたAIツールを悪用したサイバー攻撃・情報漏洩インシデント**が急増しています。

従来のEDRやセキュリティ監視ツールは、「スクリプト実行」「ファイル探索」「パッケージインストール」などを開発者の正当な通常業務プロセスとみなすため、正規の権限を持つAIエージェントを悪用した攻撃を検知することが困難です。

本ドキュメントでは、主要な脅威に対する**「GitHub CLI (gh) 等の開発ツールの安全なマウント」**、**「Microsoft Intune による一括配布」**、**「Claude Code 公式 Sandbox 機能」**、**「agy の bwrap サンドボックス化」**を体系的に記録します。

---

## 2. GitHub CLI (`gh`) などの設定マウントとセキュリティ

`bwrap` サンドボックスでは `$HOME` を空の `tmpfs` で隠蔽しているため、デフォルトでは `~/.config/gh`（GitHub CLI の認証トークン・設定）が読めず、`gh` コマンドが未認証状態になります。

### 安全な解決策（ピンポイント・Read-Only マウント）
`~/.config` 全体をマウントすると gcloud や AWS、ブラウザ等の認証情報まで見えてしまうため、**`~/.config/gh` および `~/.config/git` のみをピンポイントで Read-Only マウント** します。

```bash
--ro-bind-try "$USER_HOME/.config/gh" "$USER_HOME/.config/gh" \
--ro-bind-try "$USER_HOME/.config/git" "$USER_HOME/.config/git" \
```

これにより、**GitHub CLI や Git 設定は正常に動作しつつ、他のクラウド認証情報やブラウザセッションは完全に隠蔽** されます。

---

## 3. このPC（Linux環境）での設定手順とロールバック

### ① agy 向け bwrap 透過ラッパー

#### 設定スクリプト (`~/.local/bin/agy`)
```bash
#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="$(pwd)"
USER_HOME="$HOME"
REAL_AGY="$USER_HOME/.local/bin/agy-real"

# bwrap サンドボックス起動
exec /usr/bin/bwrap \
  --ro-bind / / \
  --dev /dev \
  --proc /proc \
  --tmpfs /tmp \
  --tmpfs "$USER_HOME" \
  --ro-bind-try "$USER_HOME/.gemini" "$USER_HOME/.gemini" \
  --bind-try "$USER_HOME/.gemini/antigravity-cli" "$USER_HOME/.gemini/antigravity-cli" \
  --bind-try "$USER_HOME/.gemini/config" "$USER_HOME/.gemini/config" \
  --bind-try "$USER_HOME/.gemini/skills" "$USER_HOME/.gemini/skills" \
  --ro-bind-try "$USER_HOME/.local" "$USER_HOME/.local" \
  --ro-bind-try "$USER_HOME/.nvm" "$USER_HOME/.nvm" \
  --ro-bind-try "$USER_HOME/.bun" "$USER_HOME/.bun" \
  --ro-bind-try "$USER_HOME/.gitconfig" "$USER_HOME/.gitconfig" \
  --ro-bind-try "$USER_HOME/.config/gh" "$USER_HOME/.config/gh" \
  --ro-bind-try "$USER_HOME/.config/git" "$USER_HOME/.config/git" \
  --ro-bind-try "$USER_HOME/.orca-remote" "$USER_HOME/.orca-remote" \
  --ro-bind-try "$USER_HOME/.orca-relay" "$USER_HOME/.orca-relay" \
  --bind "$TARGET_DIR" "$TARGET_DIR" \
  --chdir "$TARGET_DIR" \
  --unshare-pid \
  -- "$REAL_AGY" "$@"
```

#### 戻し方
```bash
rm -f ~/.local/bin/agy && mv ~/.local/bin/agy-real ~/.local/bin/agy
```

---

### ② Cloudflare 1.1.1.2 セキュアDNS

```bash
# 設定
sudo mkdir -p /etc/systemd/resolved.conf.d
sudo tee /etc/systemd/resolved.conf.d/cloudflare-security.conf << 'EOF'
[Resolve]
DNS=1.1.1.2 1.0.0.2 2606:4700:4700::1112 2606:4700:4700::1002
FallbackDNS=1.1.1.1 1.0.0.1
DNSOverTLS=opportunistic
EOF
sudo systemctl restart systemd-resolved
```

```bash
# ロールバック
sudo rm -f /etc/systemd/resolved.conf.d/cloudflare-security.conf
sudo systemctl restart systemd-resolved
```
