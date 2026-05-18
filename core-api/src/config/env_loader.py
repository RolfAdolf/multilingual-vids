from pathlib import Path

import environ


def read_env_files(root: Path, *relative_paths: str) -> None:
    for relative in relative_paths:
        path = root / relative
        if path.is_file():
            environ.Env.read_env(path)
