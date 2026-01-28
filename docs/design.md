# ADHD最適化タスク管理システム 設計仕様書

## 1. 概要（Overview）

### 1.1 目的（Purpose）

本ドキュメントは、ADHD特性に最適化された軽量タスク管理システムの設計仕様を定義する。
本システムは、低摩擦なタスク追加、即時完了フィードバック、常時可視化を重視し、5インチ常設ディスプレイ上での利用を想定する。

### 1.2 目標（Goals）

* シンプルなリスト型TODOインターフェースを提供する。
* UIからタスクの追加・編集・削除（CRUD）を可能にする。
* Slack Bot経由のAIエージェントによるタスク操作をオプションで提供する。
* 音声によるタスク追加をオプションで提供する。
* Raspberry Pi上で常時稼働し、運用コストを最小化する。

### 1.3 非目標（Non-Goals）

* ガントチャート、依存関係管理、カレンダー統合などの高度なプロジェクト管理機能。
* 複数ユーザによる同時編集やコラボレーション機能。
* クラウドSaaS型の公開サービス運用（ローカルファーストを優先）。

### 1.4 必要なハードウェア

**必須**

| アイテム | 仕様・備考 |
|---------|-----------|
| Raspberry Pi 4 Model B | 2GB以上推奨 |
| microSDカード | 32GB以上、Class 10 / A1以上 |
| USB-C電源アダプタ | 5V 3A（15W）以上 |
| micro HDMIケーブル | Pi 4はmicro HDMI出力 |
| 5インチHDMIディスプレイ | 800x480推奨 |

**推奨（常時稼働用）**

| アイテム | 仕様・備考 |
|---------|-----------|
| ヒートシンク | 貼り付けタイプ、CPU/RAM用 |
| ケース | ファン付き推奨 |

**オプション（タッチ操作する場合）**

| アイテム | 仕様・備考 |
|---------|-----------|
| タッチ対応ディスプレイ | USB接続でタッチ入力 |

---

## 2. 要件定義（Requirements）

### 2.1 機能要件（Functional Requirements）

**コア機能（MVP）**

* 未完了タスクをすべてリスト表示する。
* UIからタスクの追加、編集、削除を行う。
* タスク状態をSQLiteに永続化する。

**オプション機能**

* Slack Bot経由でAIエージェントがタスクの作成・変更・一覧取得を行う。
* 音声入力によるタスク追加を行う。

### 2.2 非機能要件（Non-Functional Requirements）

* タスク操作の低遅延（ローカル環境で100ms以下を目標）。
* 電源断に対する高い耐障害性（SQLite WALモード利用）。
* Raspberry Pi Zero / 4 / 5で稼働可能な低リソース消費。
* シンプルなデプロイおよび保守性。

---

## 3. システムアーキテクチャ（System Architecture）

### 3.1 全体構成（High-Level Architecture）

```
+----------------------+        +------------------+
|  5インチ表示UI        | <----> |  FastAPI Backend |
+----------------------+        +------------------+
                                     |
                                     v
                                 SQLite DB

(オプション: Slack Bot連携)
+------------------+    WebSocket     +-------------------+
| Slack API        | <--------------> | Raspberry Pi      |
| (Socket Mode)    |                  | - Slack Bot       |
+------------------+                  | - Claude Code CLI |
        ^                             | - FastAPI         |
        |                             +-------------------+
   ユーザー                            (外部公開不要)

音声入力（Browser / Whisper） -> FastAPI REST API
```

### 3.2 コンポーネント構成

**Raspberry Pi側**

* FastAPIサーバ（REST API + UI配信）
* SQLiteデータベース（tasks.db）
* Chromium kioskモードによる常時表示

**外部統合（オプション）**

* Slack Bot（Raspberry Pi上でSocket Modeで動作）
* Claude Code CLI（Skills経由でAPI操作）
* Socket Mode採用により外部公開（Tailscale/Cloudflare Tunnel）不要

### 3.3 Claude Code Skills構成

```
.claude/
└── skills/
    ├── add-task.md      # タスク追加
    ├── list-tasks.md    # タスク一覧取得
    ├── complete-task.md # タスク完了
    └── delete-task.md   # タスク削除
```

各Skillは定義されたスクリプト（curl等）を実行し、FastAPI REST APIを呼び出す。

---

## 4. 技術スタック（Technology Stack）

| レイヤ              | 技術                                      |
| ---------------- | --------------------------------------- |
| バックエンド           | Python, FastAPI                         |
| データベース           | SQLite（WALモード）                          |
| UI               | HTMX + Jinja2 + Tailwind CSS（または最小限CSS） |
| デバイス             | Raspberry Pi + 5インチHDMIタッチディスプレイ        |
| AIエージェント         | Claude Code CLI + Skills                |
| 外部メッセージング（オプション） | Slack Bot（slack-bolt, Socket Mode）             |
| 音声（オプション）        | Web Speech API / Whisper                |

---

## 5. データモデル（Data Model）

### 5.1 データベーススキーマ

**Table: tasks**

| カラム        | 型                | 説明                         |
| ---------- | ---------------- | -------------------------- |
| id         | TEXT PRIMARY KEY | タスク識別子（ULID推奨）             |
| title      | TEXT NOT NULL    | タスク内容                      |
| status     | TEXT NOT NULL    | 'todo', 'done', 'archived' |
| created_at | INTEGER NOT NULL | 作成時刻（Unix timestamp）       |
| updated_at | INTEGER NOT NULL | 更新時刻（Unix timestamp）       |

**インデックス**

```sql
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
```

---

## 6. API設計（API Design）

### 6.1 RESTエンドポイント

| Method | Endpoint               | 説明             |
| ------ | ---------------------- | -------------- |
| GET    | /api/tasks             | タスク一覧取得（クエリパラメータでフィルタ） |
| GET    | /api/tasks/{id}        | タスク詳細取得        |
| POST   | /api/tasks             | タスク追加          |
| PATCH  | /api/tasks/{id}        | タスク更新（タイトル・状態） |
| DELETE | /api/tasks/{id}        | タスク削除          |

### 6.2 リクエスト/レスポンス例

**POST /api/tasks**
```json
// Request
{
  "title": "買い物に行く"
}

// Response
{
  "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "title": "買い物に行く",
  "status": "todo",
  "created_at": 1706356800,
  "updated_at": 1706356800
}
```

**PATCH /api/tasks/{id}**
```json
// Request
{
  "status": "done"
}

// Response
{
  "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "title": "買い物に行く",
  "status": "done",
  "created_at": 1706356800,
  "updated_at": 1706360400
}
```

---

## 7. ユーザインターフェース設計（UI Design）

### 7.1 UI設計原則

* 未完了タスクの単一リスト表示。
* 認知負荷を下げるため階層構造やバックログ表示を排除。
* ワンタップ完了・削除操作。
* テキスト入力によるタスク追加・編集。

### 7.2 UI技術

* HTMXによる部分更新（SPA不要）。
* FastAPI + Jinja2によるテンプレートレンダリング。
* Tailwind CSSまたは最小限のカスタムCSS。

### 7.3 画面構成

```
+----------------------------------+
|  TODO                            |
+----------------------------------+
| [ 新しいタスクを入力...    ] [+] |
+----------------------------------+
| ○ 買い物に行く              [×] |
| ○ メールを返信する          [×] |
| ○ レポートを書く            [×] |
+----------------------------------+
```

---

## 8. 外部連携設計（External Integration）

### 8.1 Slack Bot連携

**採用理由**

* 仕事用Slackとの統合が可能
* Socket Modeを利用可能（Raspberry Piからの外向き接続のみ）
* Webhook方式と異なり、ポート開放やトンネル構築が不要

**接続方式: Socket Mode (WebSocket)**

```
Raspberry Pi (Slack Bot)
        |
        | WebSocket接続を維持（外向きWSS）
        v
Slack API サーバー
        ^
        |
   ユーザー（Slackアプリ）
```

* Raspberry Piがインターネットに外向き接続できれば動作
* ファイアウォール設定やポート開放は不要
* Tailscale / Cloudflare Tunnel は不要
* 接続断時は slack-bolt が自動再接続 + systemd の Restart で対応

### 8.2 Slack App設定

1. https://api.slack.com/apps でApp作成
2. **Socket Mode** を有効化
3. **App-Level Token** を生成（`connections:write` スコープ）
4. **Bot Token Scopes** を設定:
   - `chat:write` - メッセージ送信
   - `app_mentions:read` - メンション読み取り
   - `im:history` - DM履歴読み取り
   - `im:read` - DM読み取り
   - `im:write` - DM送信
5. **Event Subscriptions** で以下を購読:
   - `message.im` - DMメッセージ
   - `app_mention` - メンション
6. Workspaceにインストール

### 8.3 Bot連携フロー

```
1. ユーザーがSlack BotにDMまたはメンション
   例: 「買い物をタスクに追加して」

2. Raspberry Pi上のBotがSocket Mode経由でメッセージ受信

3. BotがClaude Code CLIを呼び出し
   claude -p "ユーザーリクエスト: 買い物をタスクに追加して" --allowedTools "Bash(curl:*)"

4. Claude CodeがSkillを選択・実行
   /add-task "買い物"

5. SkillがFastAPI REST APIを呼び出し
   curl -X POST http://localhost:8000/api/tasks -d '{"title":"買い物"}'

6. 結果をBotがSlack経由でユーザーに返信
```

### 8.4 実装例（slack-bolt）

```python
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import subprocess
import os

app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.event("message")
def handle_message(event, say):
    # Bot自身のメッセージは無視
    if event.get("bot_id"):
        return

    user_msg = event["text"]
    # Claude Code CLI を呼び出し
    result = subprocess.run(
        ["claude", "-p", f"ユーザーリクエスト: {user_msg}",
         "--allowedTools", "Bash(curl:*)"],
        capture_output=True, text=True
    )
    say(result.stdout)

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()  # Socket Mode（外部公開不要）
```

---

## 9. 音声入力設計（Voice Input, Optional）

### 9.1 ブラウザ音声入力

* Web Speech APIをUIに統合。
* 認識結果をFastAPIのタスク追加APIに送信。

### 9.2 ローカル音声認識

* Whisperをローカルまたは別端末で実行。
* 認識結果をFastAPIへ送信。

---

## 10. デプロイおよび運用（Deployment & Operations）

### 10.1 Raspberry Piセットアップ

#### 10.1.1 OS インストール

Raspberry Pi Imagerで以下を選択：
- **OS**: Raspberry Pi OS (64-bit) - Desktop版推奨（Chromium kiosk用）
- **設定**（歯車アイコン）:
  - SSH有効化（パスワード認証 or 公開鍵）
  - Wi-Fi設定（SSID, パスワード）
  - ユーザー名/パスワード設定
  - ホスト名設定（例: `raspberrypi`）

#### 10.1.2 SSH接続

SDカードをRaspberry Piに挿入し、電源投入後：

```bash
# ホスト名で接続
ssh pi@raspberrypi.local

# または IPアドレスで接続（ルーターの管理画面等で確認）
ssh pi@192.168.x.x
```

以降の作業はすべてSSH経由で実施。

#### 10.1.3 基本パッケージ

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  git \
  vim \
  python3 \
  python3-pip \
  python3-venv \
  chromium-browser \
  curl
```

#### 10.1.4 Claude Code CLI インストール

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

インストール後、認証：
```bash
claude
# 初回起動時にブラウザ認証またはAPIキー設定
```

#### 10.1.5 アプリケーションセットアップ

```bash
cd ~
git clone <repository-url> raspi_todo_app
cd raspi_todo_app

# Python仮想環境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 10.1.6 環境変数設定

```bash
# ~/raspi_todo_app/.env
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
```

`.env` は `.gitignore` に追加済みであること。

#### 10.1.7 FastAPI 自動起動（systemd）

```bash
sudo vim /etc/systemd/system/todo-app.service
```

内容：
```ini
[Unit]
Description=TODO App FastAPI
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/raspi_todo_app
Environment="PATH=/home/pi/raspi_todo_app/.venv/bin"
ExecStart=/home/pi/raspi_todo_app/.venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

有効化：
```bash
sudo systemctl daemon-reload
sudo systemctl enable todo-app
sudo systemctl start todo-app
```

#### 10.1.8 Slack Bot 自動起動（systemd）

```bash
sudo vim /etc/systemd/system/slack-bot.service
```

内容：
```ini
[Unit]
Description=Slack Bot for TODO App
After=network.target todo-app.service

[Service]
User=pi
WorkingDirectory=/home/pi/raspi_todo_app
Environment="PATH=/home/pi/raspi_todo_app/.venv/bin"
EnvironmentFile=/home/pi/raspi_todo_app/.env
ExecStart=/home/pi/raspi_todo_app/.venv/bin/python src/slack_bot.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

有効化：
```bash
sudo systemctl daemon-reload
sudo systemctl enable slack-bot
sudo systemctl start slack-bot
```

#### 10.1.9 Chromium Kioskモード（自動起動）

```bash
mkdir -p ~/.config/autostart
vim ~/.config/autostart/kiosk.desktop
```

内容：
```ini
[Desktop Entry]
Type=Application
Name=TODO Kiosk
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble http://localhost:8000
X-GNOME-Autostart-enabled=true
```

#### 10.1.10 ディスプレイ設定（5インチ HDMI）

```bash
sudo vim /boot/config.txt
```

追加（ディスプレイの仕様に応じて調整）：
```ini
# 5インチ 800x480 ディスプレイ
hdmi_group=2
hdmi_mode=87
hdmi_cvt=800 480 60 6 0 0 0
hdmi_drive=1

# タッチスクリーンの場合
dtoverlay=ads7846
```

#### 10.1.11 スクリーンセーバー無効化

```bash
sudo vim /etc/xdg/lxsession/LXDE-pi/autostart
```

追加：
```
@xset s off
@xset -dpms
@xset s noblank
```

#### 10.1.12 動作確認

```bash
# FastAPI確認
curl http://localhost:8000/api/tasks

# サービス状態確認
sudo systemctl status todo-app
sudo systemctl status slack-bot

# ログ確認
journalctl -u todo-app -f
journalctl -u slack-bot -f
```

### 10.2 ディレクトリ構成

```
raspi_todo_app/
├── docs/
│   └── design.md           # 本ドキュメント
├── src/
│   ├── main.py             # FastAPIエントリポイント
│   ├── database.py         # SQLite接続・操作
│   ├── models.py           # Pydanticモデル
│   ├── slack_bot.py        # Slack Bot（Socket Mode）
│   ├── routers/
│   │   └── tasks.py        # タスクAPIルーター
│   └── templates/
│       ├── base.html       # ベーステンプレート
│       └── index.html      # メイン画面
├── static/
│   └── style.css           # スタイルシート
├── .claude/
│   └── skills/
│       ├── add-task.md
│       ├── list-tasks.md
│       ├── complete-task.md
│       └── delete-task.md
├── tasks.db                # SQLiteデータベース
├── requirements.txt
└── README.md
```

### 10.3 バックアップ戦略

* tasks.dbの定期コピー（cronで日次）。
* 日次JSONエクスポートによる冗長バックアップ（任意）。

---

## 11. 将来拡張（Future Enhancements）

* タスク優先度・ピン留め機能。
* 完了数統計・ストリーク可視化。
* e-ink補助ディスプレイによる低刺激リマインダー。
* AIによるタスククラスタリング・再スケジューリング。

---

## 12. リスクと対策（Risks & Mitigations）

| リスク              | 対策                            |
| ---------------- | ----------------------------- |
| 電源断によるDB破損       | SQLite WALモード、定期バックアップ        |
| Slack Token漏洩        | 環境変数で管理、.envファイルをgitignore   |
| UIによる認知過負荷       | 最小限のUI設計原則を遵守                 |
| 過剰設計             | フェーズ分割による段階的開発                |

---

## 13. 実装フェーズ（Implementation Phases）

### Phase 1: MVP

* FastAPI + SQLite CRUD API
* HTMXによるリストUI
* Raspberry Pi kiosk表示

### Phase 2: 外部統合

* Claude Code Skills定義
* Slack Bot統合（Socket Mode、トンネル不要）

### Phase 3: HCI拡張

* 音声入力
* 認知フィードバック（視覚・音声報酬）

---

## 変更履歴

| 日付       | 変更内容                                           |
| ---------- | -------------------------------------------------- |
| 2026-01-27 | 初版作成                                           |
| 2026-01-27 | Slack Bot（Socket Mode）採用を決定、トンネル不要     |
| 2026-01-27 | Raspberry Pi セットアップ手順を詳細化              |
| 2026-01-27 | SSH前提のセットアップに変更、エディタをvimに統一、Vim設定同期手順削除 |
| 2026-01-27 | 必要なハードウェアリストを追加（1.4節）、Raspberry Pi 4 Model B採用 |
