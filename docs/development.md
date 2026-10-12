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
docker compose up --build --detach --wait api
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
