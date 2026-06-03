from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp_server.path_utils import find_repo_root


class SkillRegistry:
    def __init__(self, skills_root: Optional[Path] = None):
        repo_root = find_repo_root(Path(__file__))
        self.skills_root = skills_root or repo_root / "skills"
        self._skills = self._scan()

    def list(self) -> List[Dict[str, Any]]:
        return list(self._skills.values())

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._skills.get(name)

    def tool_for_route(self, route: str) -> Optional[str]:
        mapping = {
            "leetcode_coach": "leetcode_coach",
            "java_stacktrace": "java_stacktrace_analyzer",
            "nl_to_sql": "nl_to_sql_generator",
            "agent_architecture": "agent_architecture_planner",
            "langgraph": "general_model_chat",
        }
        return mapping.get(route)

    def tool_for_skill(self, skill_name: str) -> Optional[str]:
        mapping = {
            "leetcode-coach": "leetcode_coach",
            "java-stacktrace-analyzer": "java_stacktrace_analyzer",
            "nl-to-sql-generator": "nl_to_sql_generator",
            "sql-exporter": "sql_exporter",
            "langgraph-workflow": "general_model_chat",
        }
        return mapping.get(skill_name)

    def _scan(self) -> Dict[str, Dict[str, Any]]:
        skills: Dict[str, Dict[str, Any]] = {}
        if not self.skills_root.exists():
            return skills
        for directory in sorted(self.skills_root.iterdir()):
            if not directory.is_dir():
                continue
            skill_file = directory / "SKILL.md"
            readme_file = directory / "README.md"
            source = skill_file if skill_file.exists() else readme_file
            if not source.exists():
                continue
            content = source.read_text(encoding="utf-8", errors="replace")
            name = self._frontmatter_value(content, "name") or directory.name
            description = self._description(content)
            skills[name] = {
                "name": name,
                "path": str(directory),
                "description": description,
                "has_skill_file": skill_file.exists(),
                "scripts": [str(path.relative_to(directory)) for path in (directory / "scripts").glob("*.py")]
                if (directory / "scripts").exists() else [],
            }
        return skills

    def _frontmatter_value(self, content: str, key: str) -> str:
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            return ""
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.startswith(f"{key}:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _description(self, content: str) -> str:
        value = self._frontmatter_value(content, "description")
        if value:
            return value
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and stripped != "---":
                return stripped[:240]
        return ""
