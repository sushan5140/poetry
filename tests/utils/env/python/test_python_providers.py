from __future__ import annotations

import sys

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from poetry.core.constraints.version import Version

from poetry.utils.env.python import Python
from poetry.utils.env.python.providers import PoetryPythonPathProvider
from poetry.utils.env.python.providers import ShutilWhichPythonProvider


if TYPE_CHECKING:
    from tests.types import MockedPoetryPythonRegister


def test_shutil_which_python_provider() -> None:
    provider = ShutilWhichPythonProvider.create()
    assert provider
    pythons = list(provider.find_pythons())
    assert len(pythons) == 1
    assert pythons[0].minor == sys.version_info.minor


@pytest.mark.skipif(sys.platform == "win32", reason="pyenv shims are POSIX scripts")
def test_shutil_which_python_provider_skips_broken_shim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # pyenv's shim exists on PATH even when no Python executable is selected.
    shim = tmp_path / "python"
    shim.write_text("#!/bin/sh\nexit 127\n", encoding="utf-8")
    shim.chmod(0o755)
    monkeypatch.setattr(
        "poetry.utils.env.python.providers.shutil.which", lambda name: str(shim)
    )
    # The fallback finder may locate other interpreters on the test machine.
    monkeypatch.setattr(
        "poetry.utils.env.python.manager.findpython.find", lambda name: None
    )

    assert ShutilWhichPythonProvider.find_python_by_name("python") is None
    assert list(ShutilWhichPythonProvider().find_pythons()) == []
    assert Python.get_active_python() is None


def test_poetry_python_path_provider_no_pythons() -> None:
    provider = PoetryPythonPathProvider.create()
    assert provider
    assert not provider.paths


def test_poetry_python_path_provider(
    mocked_poetry_managed_python_register: MockedPoetryPythonRegister,
) -> None:
    cpython_path = mocked_poetry_managed_python_register("3.9.1", "cpython")
    pypy_path = mocked_poetry_managed_python_register("3.10.8", "pypy")
    free_threaded_path = mocked_poetry_managed_python_register(
        "3.13.2", "cpython", free_threaded=True, with_install_dir=True
    )

    provider = PoetryPythonPathProvider.create()

    assert provider

    assert set(provider.paths) == {cpython_path, pypy_path, free_threaded_path}
    assert len(list(provider.find_pythons())) == 4

    assert provider.installation_bin_paths(Version.parse("3.9.1"), "cpython") == [
        cpython_path
    ]
    assert provider.installation_bin_paths(Version.parse("3.9.2"), "cpython") == []
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "pypy") == [
        pypy_path
    ]
    assert provider.installation_bin_paths(Version.parse("3.10.8"), "cpython") == []
    assert provider.installation_bin_paths(
        Version.parse("3.13.2"), "cpython", free_threaded=True
    ) == [free_threaded_path]
