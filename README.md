# 🔔 Website Update Monitor

自動でウェブサイトの更新を監視し、新着コンテンツをメール通知するシステムです。  
GitHub Actionsを使用して完全無料で24/365稼働します。

## ✨ Features

- 🤖 **完全自動化** - 定期的にウェブサイトをチェック
- 📧 **メール通知** - 新着コンテンツを美しいHTMLメールで送信
- 💰 **完全無料** - GitHub Actionsを使用、サーバー不要
- 🔒 **セキュア** - 認証情報はGitHub Secretsで安全に管理
- 📊 **重複防止** - キャッシュ機構により同じコンテンツは通知しない

## 🚀 Quick Start

### 1. Fork this repository

このリポジトリをForkしてください。

### 2. Set up GitHub Secrets

リポジトリの Settings > Secrets and variables > Actions で以下を設定：

| Secret Name | Description | Example |
|------------|-------------|---------|
| `EMAIL_ADDRESS` | 送信元・送信先メールアドレス | `your-email@gmail.com` |
| `EMAIL_PASSWORD` | Gmailアプリパスワード（16文字） | `abcd1234efgh5678` |
| `GH_PAT` | GitHub Personal Access Token | `github_pat_xxxxx` |

### 3. Set up environment variables (Optional)

必要に応じて、以下の環境変数をSecretsに追加：

| Secret Name | Description | Default |
|------------|-------------|---------|
| `TARGET_URL` | 監視対象URL | `https://example.com` |
| `TARGET_NAME` | サイト名（メールに表示） | `ウェブサイト` |
| `EXCLUDE_TEXTS` | 除外するテキスト（\|区切り） | `""` |

### 4. Customize schedule

`.github/workflows/check_blog.yml` の cron 設定を編集：

```yaml
schedule:
  - cron: '0 0 * * *'  # 毎日午前9時（日本時間）
