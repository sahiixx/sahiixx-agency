from __future__ import annotations

from pathlib import Path

from sahiixx_agency.discovery.entrypoint import detect_project_type, infer_entrypoint


def test_node_project(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"scripts": {"dev": "next dev"}}')
    assert detect_project_type(tmp_path) == "node"
    assert infer_entrypoint(tmp_path) == [["npm", "install"], ["npm", "run", "dev"]]


def test_python_project(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "requirements.txt").write_text("requests\n")
    assert detect_project_type(tmp_path) == "python"
    assert infer_entrypoint(tmp_path) == [
        ["pip", "install", "-r", "requirements.txt"],
        ["python", "main.py"],
    ]


def test_makefile_project(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("run:\n\techo hi\n")
    assert detect_project_type(tmp_path) == "make"
    assert infer_entrypoint(tmp_path) == ["make", "run"]


def test_unknown_project(tmp_path: Path) -> None:
    assert detect_project_type(tmp_path) == "unknown"
    assert infer_entrypoint(tmp_path) is None


def test_inferred_commands_are_shell_safe(tmp_path: Path) -> None:
    """Inferred entrypoints must never contain shell metacharacters like '&&'."""
    (tmp_path / "package.json").write_text('{"scripts": {"dev": "next dev"}}')
    entrypoint = infer_entrypoint(tmp_path)
    assert entrypoint == [["npm", "install"], ["npm", "run", "dev"]]
    assert isinstance(entrypoint, list)
    for step in entrypoint:
        assert isinstance(step, list)
        assert "&&" not in step
