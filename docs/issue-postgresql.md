# B2：PostgreSQLへの実接続と保存を検証する

対象マイルストーンはM2。想定60〜90分。2026-11-05に利用者が選択。[GitHub Issue #11](https://github.com/shogo-ito-4423/request-log-01/issues/11)。

## 背景・解決する問題

B1（Issue #8）でSQLite専用の接続引数を分離したが、モックによる単体テストではドライバ読み込み・認証・ネットワーク・実DBへの保存を確認できない。現行ComposeはSQLiteのみを使用し、PostgreSQLドライバも未導入。

## 実装範囲

- プロジェクト専用のPostgreSQLサービスと名前付きボリュームをComposeで管理する。
- PostgreSQLドライバをコンテナの依存関係に追加し、ロックファイルを更新する。
- APIの接続先を設定し、独立した検証環境で実HTTP経由の保存・取得を確認する。
- 起動・検証・停止手順と設計判断を文書化する。

## 完了条件

- Docker ComposeでPostgreSQLとAPIが起動し、ヘルスチェックが成功する。
- API経由で登録した要望を、返されたIDで取得し、登録内容と照合できる。
- 検証用API・DBコンテナの再作成後も、同じIDと内容を取得できる。
- 既存のSQLiteデータと既存Dockerリソースを変更せず、検証環境を分離する。
- 既存テストとRuffの静的解析・整形チェックがコンテナ内で成功する。
- 使用した構成、検証コマンドと結果、残作業を記録する。ローカル検証・CI・マージを区別する。

## 技術・依存関係

PostgreSQL、Docker Compose、SQLAlchemy、DBドライバ、接続URL、名前付きボリューム。依存B1（Issue #8）は完了。AlembicはB3、DELETEはB4、PostgreSQL統合テストのCI組込みはB5で扱う。

## 着手時点

利用者と接続・検証方針を整理してから実装する。ローカルにPostgreSQL 15のイメージがある。外部イメージの取得が必要になった場合は取得前に承認を得る。永続ボリュームは明示的な許可なく削除しない。

## ローカル実装・検証結果（2026-11-05）

- `compose.postgresql.yaml` に独立したAPI・DB・test構成を追加。DBのhealthcheck成功後にAPIが起動する。DBのホストポート公開はなし。
- ローカルに存在するPostgreSQL 15イメージをdigestで固定して使用。外部DBイメージの取得なし。
- `psycopg[binary]` を追加し、コンテナ内のpip-toolsで両ロックを更新。解決バージョンは3.3.8。既存依存のバージョン変更なし。
- 検証コマンドは開発手順と同じで、各Composeコマンドに `-p request-log-01-b2-check` を付けて専用環境を使用した。
- Compose設定検証とAPI・testイメージのビルド成功。API・DBともHealthy。
- 既存 `scripts/smoke.py` による実HTTP登録・更新・取得、404/422の確認成功。再作成前後のverifyでIDと全フィールドの一致を確認。
- `up --pull never --detach --force-recreate --wait db api` でAPI・DBの両コンテナを再作成後、verifyが成功。DB内のpsqlでもID=1、タイトル・status・priority・assigneeを確認。
- 全55テスト成功、Ruff check・format check成功、アプリのカバレッジ100%。既存のStarlette/httpx非推奨警告が1件。
- 検証用コンテナ・ネットワークは `down` で削除。`request-log-01-b2-check_postgres-data` と `request-log-01-b2-check_smoke-state` は保持。
- ローカルの実装・動作検証は完了。実績時間は未計測。
- 利用者からマージまでの依頼を受け、Issue #11を起票。`codex/b2-postgresql` からPR・CI確認・マージへ進む。最終状態は進捗台帳に記録する。
