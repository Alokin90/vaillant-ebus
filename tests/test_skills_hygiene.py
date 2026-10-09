"""Hygiene checks for the project agent skills under .agents/skills (frontmatter, language, secrets)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SKILLS = Path(__file__).resolve().parents[1] / ".agents" / "skills"
DUTCH_STOPWORDS = re.compile(
    r"\b(het|een|niet|voor|zijn|wordt|geen|naar|deze|altijd|nooit|maar|zodat|moet|alleen|waar|maken)\b", re.IGNORECASE
)
SECRET_ASSIGNMENT = re.compile(
    r"""(?:PASS|PASSWORD|TOKEN|SECRET)\s*=\s*["'](?!\$|<|your_|PASSWORD|\{)[^"'\s]{6,}["']"""
)


# Intent: list every markdown file of every project skill.
# Why: the same hygiene rules apply to SKILL.md and REFERENCE.md.
def skill_files() -> list[Path]:
    return sorted(SKILLS.glob("*/*.md"))


# Intent: split a skill file into its YAML frontmatter and body, normalizing line endings.
# Why: some skill files are checked out with CRLF on Windows.
def split_frontmatter(path: Path) -> tuple[dict[str, object] | None, str]:
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if match is None:
        return None, text
    return yaml.safe_load(match.group(1)), match.group(2)


# Intent: every SKILL.md has valid frontmatter whose name matches its directory and a non-empty description.
# Why: skill loaders read the frontmatter; a broken or missing one silently disables the skill.
@pytest.mark.parametrize("path", sorted(SKILLS.glob("*/SKILL.md")), ids=lambda p: p.parent.name)
def test_skill_frontmatter_is_valid(path: Path) -> None:
    frontmatter, _ = split_frontmatter(path)

    assert frontmatter is not None, f"{path} has no frontmatter"
    assert frontmatter.get("name") == path.parent.name
    assert str(frontmatter.get("description", "")).strip()


# Intent: skills are written in English (trigger keywords in the frontmatter may stay multilingual).
# Why: one language keeps instructions searchable and reviewable; the project agreed on English in 1.10.5.
@pytest.mark.parametrize("path", skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_skill_prose_is_english(path: Path) -> None:
    _, body = split_frontmatter(path)
    prose = "\n".join(line for line in body.split("\n") if not line.startswith(("    ", "\t")))

    assert not DUTCH_STOPWORDS.findall(prose), f"Dutch prose found in {path.name}"


# Intent: skills never hold credential literals; they reference environment variables or placeholders.
# Why: a plaintext password was once committed in the home-assistant skill.
@pytest.mark.parametrize("path", skill_files(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_skill_files_contain_no_credential_literals(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    assert SECRET_ASSIGNMENT.search(text) is None, f"credential-like assignment in {path.name}"
