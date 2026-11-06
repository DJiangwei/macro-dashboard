"""scripts/env_file.sh must read .env.local the way the Python loaders do."""
import os
import subprocess


def _load(tmp_path, text: str) -> tuple[dict[str, str], str]:
    env_file = tmp_path / ".env.local"
    env_file.write_text(text)
    result = subprocess.run(
        ["sh", "-c", '. scripts/env_file.sh && load_env_file "$1" && env', "sh", str(env_file)],
        capture_output=True,
        text=True,
        env={"PATH": os.environ["PATH"]},
    )
    assert result.returncode == 0, result.stderr
    loaded = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    return loaded, result.stderr


def test_values_are_read_literally_with_spaces_quotes_and_comments(tmp_path) -> None:
    loaded, stderr = _load(
        tmp_path,
        "# keys\n"
        "\n"
        "SPACED_TOKEN = ab$cdEF12\n"
        "SINGLE='x$y z'\n"
        'DOUBLE="plain"\n'
        "export EXPORTED=1\n"
        "WINDOWS=crlf\r\n"
        "LAST=end",
    )
    assert loaded["SPACED_TOKEN"] == "ab$cdEF12"
    assert loaded["SINGLE"] == "x$y z"
    assert loaded["DOUBLE"] == "plain"
    assert loaded["EXPORTED"] == "1"
    assert loaded["WINDOWS"] == "crlf"
    assert loaded["LAST"] == "end"
    assert stderr == "", "the loader must never echo a value fragment in an error"
