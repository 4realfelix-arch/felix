"""Regression tests for AuthManager session file compatibility.

We’ve had historical session formats where `data/sessions.json` included fields that
no longer exist on `AuthSession` (e.g. `messages`, `state`, etc). The loader should
ignore unknown keys and never crash.
"""

import json
import time


def test_auth_manager_load_sessions_ignores_legacy_fields(tmp_path, monkeypatch):
    from server import auth as auth_mod

    # Redirect auth module storage into temp dir
    monkeypatch.setattr(auth_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(auth_mod, "USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr(auth_mod, "SESSIONS_FILE", tmp_path / "sessions.json")

    now = time.time()

    # Legacy-ish payload: includes keys not present on AuthSession
    legacy = {
        "tok_1": {
            "token": "tok_1",
            "username": "admin",
            "created_at": now - 10,
            "expires_at": now + 3600,
            "ip_address": "127.0.0.1",
            "messages": [{"role": "user", "content": "hello"}],
            "state": "LISTENING",
            "last_activity": now,
            "speaking_started": None,
        }
    }

    auth_mod.SESSIONS_FILE.write_text(json.dumps(legacy))

    mgr = auth_mod.AuthManager()

    assert "tok_1" in mgr._sessions
    sess = mgr._sessions["tok_1"]
    assert sess.username == "admin"
