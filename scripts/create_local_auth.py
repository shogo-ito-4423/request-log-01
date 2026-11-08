"""Create ignored local demo credentials without overwriting existing configuration."""

import hashlib
import json
import os
import secrets
from pathlib import Path


def main():
    users = []
    lines = []
    for name, role, variable in (
        ("alice", "user", "API_TOKEN"),
        ("bob", "user", "BOB_TOKEN"),
        ("manager", "admin", "ADMIN_TOKEN"),
    ):
        token = secrets.token_urlsafe(32)
        users.append(
            {
                "user_id": name,
                "role": role,
                "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            }
        )
        lines.append(f"{variable}={token}")
    lines.append("AUTH_USERS_JSON='" + json.dumps(users) + "'")
    path = Path(".env")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write("\n".join(lines) + "\n")
    print("Created .env for local demos; do not share or commit it.")


if __name__ == "__main__":
    main()
