import pathlib


def pytest_ignore_collect(collection_path: pathlib.Path, config):
    """Keep the default test run fast.

    The repo vendors ComfyUI which contains a large integration-style test suite
    under `comfy/tests/**` that imports torch and starts servers. Those tests are
    valuable, but they should be opt-in.

    To run them explicitly:
      - `pytest comfy/tests -m inference`
      - `pytest comfy/tests -m integration`
      - or remove the default marker expression in `pytest.ini`.
    """

    # Opt-in if user explicitly asked for the markers.
    markexpr = getattr(config.option, "markexpr", "") or ""
    if "integration" in markexpr or "inference" in markexpr:
        return False

    # Skip Comfy's own test suite by default.
    path_str = str(collection_path)
    return "/comfy/tests/" in path_str or path_str.endswith("/comfy/tests")
