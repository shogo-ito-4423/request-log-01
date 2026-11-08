# Request Log — 業務改善リクエスト管理API

[![CI](https://github.com/shogo-ito-4423/request-log-01/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/shogo-ito-4423/request-log-01/actions/workflows/ci.yml)

業務で見つけた改善要望を登録し、担当者・優先度・進捗を管理するREST APIです。
2026年10月12日の1日版MVPとして、要件整理 → API実装 → DB保存 → 自動テスト → CIまでを対象にしています。

開発履歴: [Issue #1](https://github.com/shogo-ito-4423/request-log-01/issues/1) →
`feat/1-minimal-api-ci` → [PR #2](https://github.com/shogo-ito-4423/request-log-01/pull/2)。

## 最短で試す

前提は、起動済みのDocker Engine / Docker DesktopとDocker Compose v2です。
Pythonやライブラリをホストにインストールする必要はありません。

```sh
git clone https://github.com/shogo-ito-4423/request-log-01.git
cd request-log-01
# 初回のみ。既存の.envは上書きしない。ローカル専用の利用者別トークンを生成する
docker run --pull=never --rm --network none -v "$PWD:/work" -w /work python:3.12-slim python scripts/create_local_auth.py
docker compose build api
docker compose run --rm --no-deps api alembic upgrade head
docker compose up --detach --wait api
```

- API操作画面（Swagger UI）: <http://localhost:8000/docs>
- OpenAPI仕様: <http://localhost:8000/openapi.json>
- ヘルスチェック: <http://localhost:8000/health>

`/issues` の全操作に認証が必要です。Swagger UIのAuthorizeへ `.env` の
`API_TOKEN`（alice）、`BOB_TOKEN`（bob）、`ADMIN_TOKEN`（manager）の値を入力します。
一般利用者は全件閲覧・自分の要望の登録／更新／削除、管理担当者は全件操作できます。
`owner_id` は認証情報から決まり、入力・変更できません。既存の所有者未設定の要望は
管理担当者だけが変更できます。設定・失効・公開時の制約は[認証運用](docs/authentication.md)を参照。

8000番が使用中の場合は `PORT=18000 docker compose up --build --detach --wait api` を実行し、URLのポートを18000に変更します。
初回ビルドはDocker HubとPyPIへの接続が必要です。Swagger UIも外部CDNを利用します。

上記は空のDB向けです。以前の版で作成したDBには、そのままupgradeせず
[既存DBの扱い](docs/development.md#既存dbの扱い)を確認してください。
APIはテーブルを自動作成しません。スキーマはAlembicで管理します。

## API仕様

| Method | Endpoint | 正常時 | 用途 |
|---|---|---|---|
| GET | `/health` | 200 | DB疎通確認（失敗時503） |
| POST | `/issues` | 201 | 改善要望を登録。Locationヘッダーに詳細URLを返す |
| GET | `/issues?limit=50&offset=0` | 200 | ID昇順の一覧（最大100件）。任意の `status` で絞り込み可能 |
| GET | `/issues/{id}` | 200 | 詳細を取得 |
| PATCH | `/issues/{id}` | 200 | 指定したフィールドだけ更新 |
| DELETE | `/issues/{id}` | 204 | 指定した要望を物理削除（本文は空） |

| フィールド | ルール | 作成時の初期値 |
|---|---|---|
| `title` | 必須、前後の空白除去後1〜200文字 | なし |
| `description` | 最大10,000文字 | 空文字 |
| `status` | `open` / `in_progress` / `done` | `open` |
| `priority` | `low` / `medium` / `high` | `medium` |
| `assignee` | 前後の空白除去後1〜100文字、またはnull | null |
| `id` | サーバー採番、変更不可 | 自動 |
| `created_at`, `updated_at` | UTCの日時、変更不可 | 自動 |

存在しないIDは404、不正な入力は422です。未知のフィールドは拒否します。
PATCHは最低1フィールドが必要で、省略フィールドを保持します。
`assignee: null` は担当解除、それ以外のフィールドに明示的なnullは指定できません。
状態遷移の順序制約は設けていません（完了から再オープンも可能）。

## 操作例

以下はデータが空の場合の例です。登録結果の `id` を後続のURLに指定してください。
curlを利用できる環境、または上記Swagger UIで操作できます。
以下の `/issues` 向けcurlには `-H 'Authorization: Bearer <本人のトークン>'` を加えます。
トークンをコマンド履歴に残さないため、通常はSwagger UIを使用してください。

```sh
curl -i http://localhost:8000/health

curl -i -X POST http://localhost:8000/issues \
  -H 'Content-Type: application/json' \
  -d '{"title":"月次集計の転記を自動化したい","description":"毎月の手作業を減らす","priority":"high"}'

curl http://localhost:8000/issues
# 対応中の要望だけをID昇順に並べ、先頭を1件飛ばして次の1件を取得
curl 'http://localhost:8000/issues?status=in_progress&offset=1&limit=1'
curl http://localhost:8000/issues/1

curl -X PATCH http://localhost:8000/issues/1 \
  -H 'Content-Type: application/json' \
  -d '{"status":"in_progress","assignee":"担当A"}'

# 上で登録したデモ用の要望を削除。成功時は204で本文は空
curl -i -X DELETE http://localhost:8000/issues/1
# 同じIDを再度削除すると404と {"detail":"Issue not found"} が返る

# 異常系: 空白だけのタイトルは422
curl -i -X POST http://localhost:8000/issues \
  -H 'Content-Type: application/json' -d '{"title":" "}'
```

## テスト・静的解析（コンテナ内）

```sh
docker compose --profile test build test
docker compose --profile test run --rm test
```

Ruffの静的解析・整形チェックとpytestを順に実行します。
テストごとに一時ディレクトリにSQLite DBを作るため、APIの保存データには触れません。
アプリのカバレッジ下限は90%です。

PostgreSQLの全CRUD・移行往復は、DBを分離した専用Compose構成で検証します。
GitHub Actionsでも既存のSQLite検証と別ジョブで実行します。
実行方法は[PostgreSQL統合テスト](docs/development.md#postgresql統合テストb5)を参照してください。

主な検証対象は、作成→詳細→一覧→更新の一連の操作、404/422、更新失敗時のデータ保持、
ページ分割、UTC日時、DB障害時の503、アプリ再生成後の永続化です。
GitHub Actionsはpush/PRごとに同じコンテナで検証し、さらに実HTTP通信とAPIコンテナ再作成後のデータ保持を確認します。

## 永続化・停止

PostgreSQLで動かす場合は、独立した `compose.postgresql.yaml` を使用します。
SQLiteの既存データは移行・変更しません。起動・登録・再作成後の検証は
[PostgreSQLの開発手順](docs/development.md#postgresqlでのローカル検証b2)を参照してください。

SQLiteファイルはコンテナ内の `/data/issues.db` にあり、Dockerの名前付きボリューム `issue-data` に保存されます。

```sh
# 停止・コンテナ削除。DBは保持される
docker compose down

# 再起動して以前の要望を取得できる
docker compose up --detach --wait api
```

`docker compose down --volumes` はDBを含むボリュームを削除します。データを破棄するときだけ使用してください。

## 設計と範囲

```mermaid
flowchart LR
    User[利用者 / Swagger UI] --> API[FastAPI / Pydantic]
    API --> ORM[SQLAlchemy Session]
    ORM --> DB[(SQLite / Docker volume)]
    Push[push / Pull Request] --> CI[GitHub Actions]
    CI --> Test[Ruff / pytest / HTTP・永続化検証]
```

- FastAPI: 入力検証とOpenAPIドキュメントをAPI定義と一緒に管理。
- SQLAlchemy: HTTPスキーマとDBモデルを分離し、リクエスト単位でSessionを閉じる。
- SQLite: 1日版のセットアップを小さくし、ファイルDBで永続化を実証。
- Docker: 実行・テスト・依存関係の解決をコンテナ内に統一。非rootユーザーでAPIを実行。
- ロックファイル: 推移的依存関係もバージョンとハッシュを固定。

一覧で状態を省略すると全状態が対象です。有効な状態で該当する要望がなければ200と空配列、未定義の状態なら422を返します。
認証、キーワード検索、削除、Alembic、クラウドデプロイは後続版の対象です。
PostgreSQLはローカル検証用構成を用意しています。PostgreSQL統合テストのCI組込みは後続版で行います。
この版はローカルデモ用で、Composeでは127.0.0.1にのみポートを公開します。
初期テーブルは起動時に作成しますが、既存テーブルのスキーマ変更には対応しません。
SQLiteの同時書き込み性能と単一プロセス構成を前提としています。

詳しい設計判断と拡張方針は [docs/architecture.md](docs/architecture.md)、
開発・公開の手順は [docs/development.md](docs/development.md) を参照してください。

## 構成

```text
app/                API・入力/出力スキーマ・DBモデル
tests/              独立したSQLite DBによるAPIテスト
scripts/smoke.py     実HTTP通信とコンテナ再作成後の検証
.github/workflows/   コンテナで動くCI
docs/               要件・設計判断・開発手順・検証記録
Dockerfile          runtime / test のマルチステージビルド
compose.yaml        ローカル起動・名前付きボリューム・テスト
requirements*.lock  ハッシュ付き依存関係ロック
```

## 参考資料

- [FastAPI: SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [GitHub Actions: Pythonのビルドとテスト](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
