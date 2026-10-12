"""Exercise a running API, including persistence across container recreation."""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


def request(base_url, method, path, payload=None, expected=200):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.status == expected, (method, path, response.status)
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["create", "verify"])
    parser.add_argument("--base-url", default="http://api:8000")
    parser.add_argument("--state", default="/tmp/smoke-state.json")
    args = parser.parse_args()
    request(args.base_url, "GET", "/health")
    state = Path(args.state)
    if args.mode == "create":
        issue = request(args.base_url, "POST", "/issues", {"title": "コンテナ永続化デモ"}, 201)
        updated = request(
            args.base_url,
            "PATCH",
            f"/issues/{issue['id']}",
            {"status": "in_progress", "priority": "high", "assignee": "demo"},
        )
        state.write_text(json.dumps(updated))
        request(args.base_url, "POST", "/issues", {"title": " "}, 422)
        request(args.base_url, "GET", "/issues/2147483647", expected=404)
    else:
        saved = json.loads(state.read_text())
        actual = request(args.base_url, "GET", f"/issues/{saved['id']}")
        assert actual == saved, (actual, saved)
        assert actual in request(args.base_url, "GET", "/issues?limit=100")
    print(f"Smoke {args.mode}: PASS")


if __name__ == "__main__":
    main()
