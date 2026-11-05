# 開発・公開手順

## コンテナでの開発

ホストにはPython、pip、Ruff、pytest、GitHub CLIをインストールしない。
実行環境はDockerコンテナ。ソースコードだけを作業フォルダで編集する。

```sh
docker compose --profile test build test
docker compose --profile test run --rm test
```

整形を反映するときは、テストイメージにソースをマウントして実行する。

```sh
docker compose --profile test run --rm --user root -v "$PWD:/app" test ruff format --no-cache .
```

## 依存関係の更新

requirements.in / requirements-dev.inを変更し、専用の一時コンテナでロックを再生成する。
更新後は必ずイメージを再ビルドして検証する。

```sh
docker run --rm -v "$PWD:/work" -w /work python:3.12-slim sh -c \
  'pip install --no-cache-dir pip-tools==7.6.2 && pip-compile --generate-hashes -o requirements.lock requirements.in && pip-compile --generate-hashes -o requirements-dev.lock requirements-dev.in'
```

## 実HTTP・永続化の確認

以下はデモ用の要望を1件作成する。業務データを入れていないデモ環境で行う。

```sh
docker compose build api
docker compose run --rm --no-deps api alembic upgrade head
docker compose up --detach --wait api
docker compose exec -T api python - create --base-url http://127.0.0.1:8000 --state /data/smoke-state.json < scripts/smoke.py
docker compose up --detach --force-recreate --wait api
docker compose exec -T api python - verify --base-url http://127.0.0.1:8000 --state /data/smoke-state.json < scripts/smoke.py
```

## GitHubの履歴

実際のIssue → 作業ブランチ → Pull Request → CI成功 → Mergeを残す。
次のテンプレートは起票に使用するための文面であり、履歴そのものの代用ではない。

- [1日版の実装Issue](issue-mvp.md)
- [Pull Requestの説明](pr-mvp.md)

公開先: `shogo-ito-4423/request-log-01`。
GitHub操作にはそのリポジトリへ書き込める認証が必要。
CIの成功はGitHub Actionsの実際の実行結果で確認する。

## PostgreSQLでのローカル検証（B2）

`compose.postgresql.yaml` は独立した構成です。プロジェクト名は
`request-log-01-postgresql`、APIは `http://localhost:18082` に公開します。
ポート競合時は `PORT=18083` などを各コマンドに指定してください。
DBはホストにポート公開せず、APIからサービス名 `db` で接続します。
`psycopg[binary]` をコンテナ内に導入し、SQLAlchemyの
`postgresql+psycopg` URLで選択します。DBのhealthcheck成功後にAPIを起動します。

固定のユーザー・パスワードはローカルデモ専用です。公開環境には使用しません。
DBは専用の `postgres-data`、検証用の比較データは `smoke-state` 名前付きボリュームへ
保存します。SQLite用のボリュームとは別であり、既存データの自動移行は行いません。
テーブル作成・スキーマ変更はAlembicで行います。APIの起動処理ではDDLを実行しません。

以下はデモ用レコードを作成します。イメージ未取得時は取得の承認を得てから進めます。

```sh
docker compose -f compose.postgresql.yaml build api test
docker compose -f compose.postgresql.yaml up --pull never --detach --wait db
docker compose -f compose.postgresql.yaml run --rm --no-deps api alembic upgrade head
docker compose -f compose.postgresql.yaml up --pull never --detach --wait api
# 登録・更新後、IDと全フィールドを照合
docker compose -f compose.postgresql.yaml exec -T api python - create --base-url http://127.0.0.1:8000 --state /data/smoke-state.json < scripts/smoke.py
docker compose -f compose.postgresql.yaml exec -T api python - verify --base-url http://127.0.0.1:8000 --state /data/smoke-state.json < scripts/smoke.py
# APIとDBの両方を再作成。ボリュームは保持
docker compose -f compose.postgresql.yaml up --pull never --detach --force-recreate --wait db api
docker compose -f compose.postgresql.yaml exec -T api python - verify --base-url http://127.0.0.1:8000 --state /data/smoke-state.json < scripts/smoke.py
# 既存のSQLiteテストと接続設定の単体テスト、Ruff
docker compose -f compose.postgresql.yaml --profile test run --rm test
# 終了。名前付きボリュームとデータは保持
docker compose -f compose.postgresql.yaml --profile test down
```

既存スモークスクリプトは一覧の先頭100件にも登録レコードが含まれることを確認します。
この手順は専用の少量データ環境向けです。100件を超える環境への対応は別課題です。
PostgreSQLの全CRUD統合テストとCIへの組込みはB5で行います。

## Alembicによるスキーマ管理（B3）

初期revision `0001` は現在のissuesテーブルを作成します。接続先はAPIと同じ
`DATABASE_URL`（未指定時は `sqlite:////data/issues.db`）です。
上記の起動例は空のDB向けです。既存テーブルがある場合は次節を先に確認します。
マイグレーションはAPI起動前に一度実行し、失敗したらAPIを起動しません。
複数APIから同時に適用しないよう、起動処理とは分離しています。

`alembic current` で適用済みrevision、`alembic history` で履歴を確認できます。
新しい変更はコンテナ内で `alembic revision --autogenerate -m '変更内容'` により
下書きを作り、生成差分と制約・データ補完方法をレビューしてから適用します。
revisionファイルを保存するにはリポジトリをコンテナにマウントします。
自動生成だけでCHECK制約等の完全な照合ができたとは判断しません。
モデルのdefault/onupdateはPython側の値設定であり、初期revisionにDB側の
DEFAULTや更新トリガーは追加していません。

専用の空PostgreSQL DBでの往復検証例です。以下のプロジェクト名・DBが未使用であることを
確認してから実行します。テストは空DBを要求し、途中のdowngradeで検証用テーブルを削除します。
既存データのあるDBには実行しません。

```sh
docker compose -p request-log-01-b3-check -f compose.postgresql.yaml build api test
docker compose -p request-log-01-b3-check -f compose.postgresql.yaml up --pull never --detach --wait db
docker compose -p request-log-01-b3-check -f compose.postgresql.yaml run --rm --no-deps -e TEST_MIGRATION_DATABASE_URL=postgresql+psycopg://request_log:local_demo_only@db:5432/request_log test pytest tests/test_migrations.py --no-cov -p no:cacheprovider
docker compose -p request-log-01-b3-check -f compose.postgresql.yaml --profile test down
```

終了後もボリュームを保持します。同じDBで再実行すると空DBチェックで停止するため、
次回は新しい専用プロジェクト名を選びます。通常のテストコマンドでも、使い捨てSQLiteで
同じ往復検証を実施します。PostgreSQL版のCI組込みはB5に残します。

## 既存DBの扱い

SQLiteからPostgreSQLへのデータ移送は今回行いません。既存のSQLiteとB2のPostgreSQLの
ボリュームは保持します。旧版の `create_all` で作成したDBにはAlembic履歴がないため、
初期revisionを直接upgradeすると既存テーブルと衝突します。

取り込み時は、書き込みを停止してバックアップを取得し、復元した別DBで全列の型・NULL許可・
主キー・3つのCHECK制約と初期revisionの一致を確認します。一致した場合のみ、承認を得て
そのDBに `alembic stamp 0001` を実行し、履歴を登録する方針です。stampはテーブル作成・
構造検証・データ移行を行いません。不一致なら差分とデータ補完を扱う移行手順を別途設計します。
今回は既存DBのstampも実施しません。

`downgrade base` はissuesテーブルとそのデータを削除します。データを元に戻す操作では
ありません。実データのある環境での復旧には、バックアップ復元や前進修正を別途検討します。

参考：[Alembic公式チュートリアル](https://alembic.sqlalchemy.org/en/latest/tutorial.html)、
[stamp等のコマンド仕様](https://alembic.sqlalchemy.org/en/latest/api/commands.html)。
