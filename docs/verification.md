# 検証記録

実施日: 2026年10月12日（日本時間）

## ローカルのコンテナ検証

実行環境: 既存Docker Desktop / Linux arm64コンテナ、Python 3.12.15。
ホストにPythonパッケージやGitHub CLIを導入せず、ホストの設定を変更せずに実施。

| 検証 | 結果 |
|---|---|
| Docker test / runtimeイメージのビルド | 成功 |
| Ruff静的解析 | 成功 |
| Ruff整形チェック | 成功 |
| pytest | 48 passed |
| アプリの行カバレッジ | 100%（133 statements、下限90%） |
| 実HTTPでhealth・作成・更新・404・422 | `Smoke create: PASS` |
| APIコンテナ強制作成後の詳細・一覧 | `Smoke verify: PASS` |
| 非rootユーザーでのSQLite読み書き | 成功 |

検証コマンドはREADMEおよびdevelopment.mdに記載。

## 検証中に発見し修正した内容

- pytestのimport解決に必要な `pythonpath = ["."]` をpyproject.tomlに追加。
- Ruffで改行とimport順を修正。
- Dockerの既存ディスクがほぼ満杯だったため、今回作成した作業用コンテナ内の
  aptインデックスとダウンロード済みパッケージだけを削除し、再起動後に検証成功。
  既存の他プロジェクトのコンテナ、イメージ、ボリューム、キャッシュは削除していない。

## 既知の注意点

Starlette TestClientからhttpxの非推奨警告が1件出る。現在のロック済み構成では
48テストすべて成功している。依存関係更新時に後継クライアントへの移行を確認する。
100%は現在のアプリコードの行カバレッジであり、負荷試験や全組み合わせの保証ではない。

## GitHubでの検証

GitHub ActionsのCI履歴は以下で確認する。

- [Actions](https://github.com/shogo-ito-4423/request-log-01/actions/workflows/ci.yml)
- [実装Issue #1](https://github.com/shogo-ito-4423/request-log-01/issues/1)
- [実装PR #2](https://github.com/shogo-ito-4423/request-log-01/pull/2)
- [初回push CI成功](https://github.com/shogo-ito-4423/request-log-01/actions/runs/38213464306)
- [初回PR CI成功](https://github.com/shogo-ito-4423/request-log-01/actions/runs/38213473981)

初回CIでcheckout v4のNode.js 20非推奨とubuntu-latest切り替え予告を検出。
checkout v6をコミットSHAで固定し、Runnerをubuntu-24.04へ固定して再検証する。

GitHub上の実行結果とPR・マージ履歴を一次記録とする。
