# B1：接続引数をDB種別で分離する

対象は[GitHub Issue #8](https://github.com/shogo-ito-4423/request-log-01/issues/8)。対象マイルストーンはM2。想定45〜60分。

## 背景・目的

`app/database.py` の `make_engine` はすべてのURLにSQLite専用の接続引数を渡している。PostgreSQL導入（B2）に備え、DB種別に応じた引数を渡せるようにする。

## 完了条件

- SQLiteでは既存の `check_same_thread=False` と `timeout=10` を保持する。
- PostgreSQLのURLではSQLite専用引数を渡さない。
- ドライバ名付きURLを含めてDB種別を判定する。
- 実DBへの接続を伴わない単体テストで、エンジン生成に渡すURL・引数を検証する。
- 既存SQLite APIテストと追加テスト、Ruffの静的解析・整形チェックがコンテナ内で成功する。
- 設計判断と検証結果をレビューし、学習記録・進捗台帳へ反映する。

## 技術・依存関係

SQLAlchemyのURLとdialect、pytest、モックによる単体テストを扱う。依存するA1（Issue #1）は完了済み。PostgreSQLのサービス・ドライバ導入と実接続は後続B2で扱う。

## 着手時点

2026-11-04にB1を選択。作業ブランチは `refactor/db-specific-connect-args`。利用者と期待値を整理してからテスト・実装を進める。

## 検証結果（2026-11-04）

- `make_url(...).get_backend_name()` でDB種別を取得し、SQLiteの場合だけ既存の接続引数を設定した。
- 通常URLとドライバ名付きURLをSQLite・PostgreSQLそれぞれで検証。モックで生成回数、URL、接続引数、返り値を確認した。
- 実装前は4ケース中PostgreSQLの2ケースが失敗し、修正後は4ケースすべて成功した。
- 既存の `request-log-01-test:latest` を使用し、ソースを読み取り専用でマウント。ネットワークなしのコンテナで全55テストとRuffの静的解析・整形チェックが成功。カバレッジ100%。
- Composeの `run` が `--no-build` および `--pull` に非対応だったため、`docker run --pull=never` で既存イメージを明示した。
- 既存のStarlette/httpx非推奨警告が1件出た。
- ローカル実装・検証・記録は完了。Issue #8を起票済み。実装コミット `a523e40`、PR #9を作成。記録時点ではCI・マージ・コミット後の振り返りを確認中。
