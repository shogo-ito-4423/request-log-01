# B3：AlembicでDBスキーマの変更履歴を管理する

対象マイルストーンはM2。想定60〜90分。2026-11-05に利用者が選択。GitHub未起票。

## 背景・解決する問題

B2（Issue #11）でPostgreSQLへの実接続と永続化を確認した。現在はAPI起動時の `Base.metadata.create_all` でテーブルを作成している。スキーマ変更履歴を管理し、空のDBから同じ構造を再現する手順が必要。

## 実装範囲

- Alembicと必要な設定をコンテナ環境へ追加し、依存ロックを更新する。
- `app/models.py` の列・型・NULL許可・主キー・CHECK制約と照合した初期revisionを作成する。Python側のdefault/onupdateとDB側のデフォルトを区別する。
- マイグレーションとAPI起動時の `create_all` の役割を整理し、起動・テスト手順に反映する。具体的な方式は利用者と設計時に決める。
- 既存SQLiteおよびB2のPostgreSQLデータを保持し、既存DBの移行・履歴管理への取り込み方針を記載する。

## 完了条件

- プロジェクト専用の空の検証用PostgreSQL DBでupgrade→downgrade→upgradeを実行でき、各段階のrevisionとテーブル状態が期待どおりである。
- 初期revisionがモデルの列・制約に対応することを確認する。
- マイグレーション後のDBでAPIが起動し、登録・取得が成功する。create_allによる作成だけではマイグレーション成功の証跡としない。
- 既存のSQLiteデータとB2の保存データを変更しない。downgradeは今回専用の検証DBだけで行い、永続ボリュームは削除しない。
- 既存テストとRuffがDocker内で成功する。
- 実行手順、既存DBの扱い、検証結果と残作業を文書化する。ローカル検証・CI・マージを区別する。

## 技術・依存関係

Alembic、revision、upgrade/downgrade、DDL、SQLAlchemy metadata、Docker Compose。依存B2（Issue #11）は完了。DELETEはB4、PostgreSQLの全CRUD統合テストとマイグレーションのCI組込みはB5。既存データの実移送は本Issueの対象外。

## 着手時点

Issue文案を準備。設計対話・実装・検証は未実施。外部起票は別途承認後に行う。実績時間は未計測。

## ローカル実装・検証結果（2026-11-05）

- 利用者が設計対話後に実装を依頼。Alembic 1.20.1、Mako 1.4.3、MarkupSafe 3.0.4をコンテナ内で依存ロックへ追加。既存パッケージのバージョン変更なし。
- 初期revision `0001` に8列・主キー・3つのCHECK制約を定義。Python側のdefault/onupdateはモデルに保持。
- APIの `create_all` を削除。API起動前の明示的なupgradeへ変更し、Dockerfile・README・開発手順・SQLite CI起動手順を更新。既存DBのstampは行わない方針を記載。
- 既存テストのDBもAlembicで構築。SQLiteの往復検証を追加し、全56テスト・Ruff check/format checkが成功、アプリのカバレッジ100%。既存のStarlette/httpx非推奨警告1件。
- 未使用を確認した `request-log-01-b3-check` 専用Composeプロジェクトで、既存のPostgreSQLイメージをpullなしで起動。
- PostgreSQLの空DBで往復検証1件成功。API起動だけではテーブルが作られないこと、upgrade後のrevision `0001`、モデルとの構造差分なし、3つのCHECK制約による不正値拒否、API登録・取得、headへの再適用でデータが保持されること、downgrade後のテーブル削除とrevision解除、再upgradeを確認。
- runtimeイメージの `alembic current` は `0001 (head)`、`alembic check` は差分なし。APIを18084番で起動し、既存スモークスクリプトのcreate成功、API・DBの再作成後のverify成功。
- 既存SQLite・B2のデータは変更せず、今回のdowngradeは専用DBだけで実施。
- 検証用コンテナ・ネットワークは停止・削除済み。`request-log-01-b3-check_postgres-data` と `request-log-01-b3-check_smoke-state` は保持。
- GitHub未起票、未コミット。変更後のGitHub CI・PR・マージは未実施。PostgreSQL全CRUDのCI組込みはB5に残る。見積もり60〜90分、実績時間未計測。

## コミット後の状態（2026-11-05）

利用者の承認後、`codex/b3-alembic` に `ea4b9f1` として実装をコミット済み。振り返りも完了し、Aは○、Bは○（補足・追加質問後）、Cは○（検証の必要性を補足）。詳細は学習記録を参照。外部起票・Push・PR・変更後のGitHub CI・マージは未実施。本追記も利用者のコミット承認を得て反映。
