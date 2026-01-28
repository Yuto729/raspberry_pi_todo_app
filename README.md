# Raspberry Pi TODO App

ADHD特性に最適化された軽量タスク管理システム。Raspberry Pi + 5インチディスプレイでの常時表示を想定。

## 必要要件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## 環境構築

```bash
# リポジトリをクローン
git clone https://github.com/Yuto729/raspberry_pi_todo_app.git
cd raspberry_pi_todo_app

# 依存関係をインストール
uv sync
```

## 起動方法

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

ブラウザで http://localhost:8000 にアクセス。

## 機能

- タスクの追加（テキスト入力 + Enter）
- タスクの完了（✅ボタン）
- データはSQLite（WALモード）で永続化

## 技術スタック

- FastAPI
- HTMX
- SQLite
- Jinja2

## ディレクトリ構成

```
raspi_todo_app/
├── src/
│   ├── main.py           # エントリポイント
│   ├── db/client.py      # SQLite操作
│   ├── models/task.py    # Pydanticモデル
│   └── routers/tasks.py  # API
├── templates/            # HTMLテンプレート
├── static/               # CSS
└── tasks.db              # データベース（自動生成）
```

## 詳細設計

[docs/design.md](docs/design.md) を参照。
