#!/usr/bin/env python3
"""Generate the deterministic phase-0 client and page surface inventory.

The legacy Flask application is imported only after an isolated SQLite URL and
temporary DATA_DIR have been installed.  No request is made and no schema is
created; importing the app is used solely to inspect Flask's registered URL map.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import logging
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


sys.dont_write_bytecode = True


LEGACY_BASELINE_COMMIT = "700006dfdfa063deb4387be572911e782bcea0d9"


HTTP_METHOD_ORDER = {
    "GET": 0,
    "POST": 1,
    "PUT": 2,
    "PATCH": 3,
    "DELETE": 4,
}

PARTIAL_DIRECTORIES = {
    "assets",
    "body_end",
    "css",
    "head",
    "js",
    "layout",
    "modals",
    "panels",
    "partials",
    "scripts",
    "sections",
    "shared",
}

LAYOUT_STEMS = {
    "admin_base",
    "base",
    "bank_data_v2_base",
    "manage_base",
    "shell",
}

ADMIN_BLUEPRINT_PREFIXES = {
    "admin_pages_bp": "/admin",
    "admin_api_bp": "/admin/api",
    "admin_api_legacy_bp": "/admin",
    "coding_admin_bp": "/admin/coding",
}


JOURNEY_DEFINITIONS = (
    (
        "authentication",
        "登录认证",
        (("web", "GET", "/login"), ("api", "POST", "/api/login")),
        ("pages/login/login",),
    ),
    (
        "home_and_catalog",
        "首页与公共题目目录",
        (("web", "GET", "/hub"), ("api", "GET", "/api/quiz/subjects")),
        ("pages/hub-v2/hub-v2", "pages/subjects/subjects"),
    ),
    (
        "practice_and_answer",
        "练习与答题记录",
        (("web", "GET", "/quiz"), ("api", "POST", "/api/record_result")),
        ("pages/practice/practice", "pages/quiz/quiz"),
    ),
    (
        "learning_data",
        "学习数据与趋势",
        (("web", "GET", "/data"), ("api", "GET", "/api/data/center")),
        ("packages/data/pages/data-center-v2/data-center-v2",),
    ),
    (
        "exam",
        "考试创建与作答",
        (("web", "GET", "/exams"), ("api", "POST", "/api/exams/create")),
        ("pages/exams-select-v2/exams-select-v2", "pages/exam-run/exam-run"),
    ),
    (
        "personal_bank",
        "个人题库管理",
        (("web", "GET", "/user/banks/"), ("api", "GET", "/user/banks/api/list")),
        ("pages/my-banks-v2/my-banks-v2", "pages/bank-detail/bank-detail"),
    ),
    (
        "public_bank",
        "题库广场",
        (("web", "GET", "/public/banks"), ("api", "GET", "/api/public/banks")),
        ("pages/public-bank-v2/public-bank-v2",),
    ),
    (
        "community",
        "论坛社区",
        (("web", "GET", "/forum"), ("api", "GET", "/api/forum/boards")),
        (),
    ),
    (
        "chat",
        "站内聊天",
        (("web", "GET", "/chat"), ("api", "GET", "/api/chat/conversations")),
        (),
    ),
    (
        "campus",
        "校园课表与成绩",
        (
            ("web", "GET", "/edu-schedule"),
            ("api", "GET", "/api/edu-schedule/status"),
            ("web", "GET", "/edu-grades"),
            ("api", "POST", "/api/edu-schedule/grades/query"),
        ),
        (
            "pages/campus/campus",
            "pages/campus-schedule/campus-schedule",
            "pages/campus-grades/campus-grades",
        ),
    ),
    (
        "coding",
        "编程练习",
        (("web", "GET", "/coding/"), ("api", "GET", "/coding/api/subjects")),
        ("pages/coding-v2/coding-v2",),
    ),
    (
        "notifications",
        "通知中心",
        (("web", "GET", "/notifications"), ("api", "GET", "/api/notifications")),
        ("pages/notifications-v2/notifications-v2",),
    ),
    (
        "settings_and_profile",
        "设置与个人资料",
        (("web", "GET", "/settings"), ("api", "GET", "/api/profile")),
        ("pages/settings-center-v2/settings-center-v2", "pages/profile-view-v2/profile-view-v2"),
    ),
    (
        "administration",
        "管理后台",
        (("web", "GET", "/admin/"), ("api", "GET", "/admin/api/users")),
        ("pages/admin-v2/admin-v2",),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory Ti legacy HTML, Flask routes, mini-program pages, and admin entries."
    )
    parser.add_argument("--legacy-root", required=True, type=Path)
    parser.add_argument(
        "--miniprogram-root",
        required=True,
        type=Path,
        help="Controlled phase-0 copy root (for example Ti-Java/miniprogram), never the dirty nested worktree.",
    )
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def method_key(method: str) -> tuple[int, str]:
    return (HTTP_METHOD_ORDER.get(method, 99), method)


def normalized_methods(methods: Iterable[str]) -> list[str]:
    return sorted({method for method in methods if method not in {"HEAD", "OPTIONS"}}, key=method_key)


def relative_source(path: str | Path | None, legacy_root: Path) -> str | None:
    if not path:
        return None
    try:
        return Path(path).resolve().relative_to(legacy_root).as_posix()
    except (OSError, ValueError):
        return None


def source_ref(source: str | None, line: int | None) -> str | None:
    if source is None:
        return None
    return f"{source}:{line}" if line is not None else source


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def expression_text(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return node.__class__.__name__


def candidate_template_literals(node: ast.AST | None) -> list[str]:
    """Extract statically visible HTML choices without treating dict keys as templates."""
    if node is None:
        return []
    literal = literal_string(node)
    if literal is not None:
        return [literal] if literal.endswith(".html") else []
    candidates: list[str] = []
    if isinstance(node, ast.Dict):
        for value in node.values:
            candidates.extend(candidate_template_literals(value))
    elif isinstance(node, ast.IfExp):
        candidates.extend(candidate_template_literals(node.body))
        candidates.extend(candidate_template_literals(node.orelse))
    elif isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.BoolOp)):
        for value in node.elts if hasattr(node, "elts") else node.values:
            candidates.extend(candidate_template_literals(value))
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
        candidates.extend(candidate_template_literals(node.func.value))
        if len(node.args) >= 2:
            candidates.extend(candidate_template_literals(node.args[1]))
    return sorted(set(candidates))


class PythonSurfaceVisitor(ast.NodeVisitor):
    """Collect per-function render calls and a small local call graph."""

    def __init__(self, source: str, flask_render_template_imported: bool) -> None:
        self.source = source
        self.flask_render_template_imported = flask_render_template_imported
        self.function_stack: list[dict[str, Any]] = []
        self.functions: list[dict[str, Any]] = []
        self.render_calls: list[dict[str, Any]] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        parent_qualname = self.function_stack[-1]["qualname"] if self.function_stack else None
        qualname = f"{parent_qualname}.{node.name}" if parent_qualname else node.name
        fact = {
            "name": node.name,
            "qualname": qualname,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "parameters": [argument.arg for argument in node.args.args],
            "called_names": set(),
            "local_calls": [],
            "render_calls": [],
            "template_bindings": {},
        }
        self.functions.append(fact)
        self.function_stack.append(fact)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def _candidates(self, node: ast.AST | None) -> list[str]:
        candidates = candidate_template_literals(node)
        if self.function_stack and isinstance(node, ast.Name):
            candidates.extend(self.function_stack[-1]["template_bindings"].get(node.id, []))
        if (
            self.function_stack
            and isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.attr == "get"
        ):
            candidates.extend(
                self.function_stack[-1]["template_bindings"].get(node.func.value.id, [])
            )
        return sorted(set(candidates))

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        if self.function_stack:
            candidates = candidate_template_literals(node.value)
            if candidates:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.function_stack[-1]["template_bindings"][target.id] = candidates
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if self.function_stack and isinstance(node.target, ast.Name):
            candidates = candidate_template_literals(node.value)
            if candidates:
                self.function_stack[-1]["template_bindings"][node.target.id] = candidates
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = call_name(node.func)
        if self.function_stack and name:
            self.function_stack[-1]["called_names"].add(name)
            self.function_stack[-1]["local_calls"].append(
                {
                    "name": name,
                    "positional_candidates": [self._candidates(argument) for argument in node.args],
                    "keyword_candidates": {
                        keyword.arg: self._candidates(keyword.value)
                        for keyword in node.keywords
                        if keyword.arg is not None
                    },
                }
            )
        if name == "render_template" and self.flask_render_template_imported:
            first_arg = node.args[0] if node.args else None
            literal = literal_string(first_arg)
            current_function = self.function_stack[-1] if self.function_stack else None
            call = {
                "source": source_ref(self.source, node.lineno),
                "source_path": self.source,
                "line": node.lineno,
                "function": current_function["qualname"] if current_function else None,
                "template": literal,
                "expression": literal if literal is not None else expression_text(first_arg),
                "resolution": "literal" if literal is not None else "dynamic",
                "candidate_templates": self._candidates(first_arg),
            }
            self.render_calls.append(call)
            if current_function is not None:
                current_function["render_calls"].append(call)
        self.generic_visit(node)


def analyze_python_sources(legacy_root: Path) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    functions_by_source: dict[str, list[dict[str, Any]]] = {}
    render_calls: list[dict[str, Any]] = []
    for path in sorted((legacy_root / "app").rglob("*.py")):
        source = path.relative_to(legacy_root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=source)
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise RuntimeError(f"Cannot parse {source}: {exc}") from exc
        flask_render_template_imported = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "flask"
            and any(alias.name == "render_template" for alias in node.names)
            for node in tree.body
        )
        visitor = PythonSurfaceVisitor(source, flask_render_template_imported)
        visitor.visit(tree)
        functions_by_source[source] = visitor.functions
        render_calls.extend(visitor.render_calls)

    for facts in functions_by_source.values():
        for fact in facts:
            fact["called_names"] = sorted(fact["called_names"])
    render_calls.sort(key=lambda item: (item["source_path"], item["line"], item["expression"] or ""))
    return functions_by_source, render_calls


def locate_function(
    functions_by_source: dict[str, list[dict[str, Any]]],
    source: str | None,
    function_name: str | None,
    source_line: int | None,
) -> dict[str, Any] | None:
    if source is None or function_name is None:
        return None
    candidates = [fact for fact in functions_by_source.get(source, []) if fact["name"] == function_name]
    if not candidates:
        return None
    if source_line is None:
        return min(candidates, key=lambda fact: (fact["qualname"].count("."), fact["start_line"]))
    containing = [
        fact for fact in candidates if fact["start_line"] <= source_line <= fact["end_line"]
    ]
    if containing:
        return min(containing, key=lambda fact: fact["end_line"] - fact["start_line"])
    return min(candidates, key=lambda fact: abs(fact["start_line"] - source_line))


def route_render_calls(
    functions_by_source: dict[str, list[dict[str, Any]]],
    source: str | None,
    route_function: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if source is None or route_function is None:
        return []
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in functions_by_source.get(source, []):
        by_name[fact["name"]].append(fact)

    collected: list[dict[str, Any]] = []
    seen_functions: set[tuple[str, int, tuple[tuple[str, tuple[str, ...]], ...]]] = set()

    def walk(fact: dict[str, Any], chain: list[str], bindings: dict[str, list[str]]) -> None:
        binding_identity = tuple(sorted((name, tuple(values)) for name, values in bindings.items()))
        identity = (fact["qualname"], fact["start_line"], binding_identity)
        if identity in seen_functions:
            return
        seen_functions.add(identity)
        for call in fact["render_calls"]:
            candidates = list(call["candidate_templates"])
            if call["resolution"] == "dynamic" and call["expression"] in bindings:
                candidates.extend(bindings[call["expression"]])
            collected.append(
                {
                    "template": call["template"],
                    "expression": call["expression"],
                    "resolution": call["resolution"],
                    "candidate_templates": sorted(set(candidates)),
                    "source": call["source"],
                    "via_functions": chain,
                    "mapping_kind": "direct" if len(chain) == 1 else "same_module_helper",
                }
            )
        for local_call in fact["local_calls"]:
            called_name = local_call["name"]
            candidates = [candidate for candidate in by_name.get(called_name, []) if "." not in candidate["qualname"]]
            if len(candidates) == 1:
                candidate = candidates[0]
                helper_bindings: dict[str, list[str]] = {}
                for index, values in enumerate(local_call["positional_candidates"]):
                    if index < len(candidate["parameters"]) and values:
                        helper_bindings[candidate["parameters"][index]] = values
                for name, values in local_call["keyword_candidates"].items():
                    if values:
                        helper_bindings[name] = values
                walk(candidate, [*chain, candidate["qualname"]], helper_bindings)

    walk(route_function, [route_function["qualname"]], {})
    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for call in collected:
        key = (
            call["template"],
            call["expression"],
            tuple(call["candidate_templates"]),
            call["source"],
            tuple(call["via_functions"]),
        )
        unique[key] = call
    return sorted(
        unique.values(),
        key=lambda item: (
            item["template"] or "",
            item["expression"] or "",
            item["candidate_templates"],
            item["source"] or "",
            item["via_functions"],
        ),
    )


def runtime_routes(
    app: Any,
    legacy_root: Path,
    functions_by_source: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rules = sorted(
        app.url_map.iter_rules(),
        key=lambda rule: (rule.rule, normalized_methods(rule.methods), rule.endpoint),
    )
    for rule in rules:
        methods = normalized_methods(rule.methods)
        view = app.view_functions.get(rule.endpoint)
        unwrapped = inspect.unwrap(view) if view is not None else None
        view_source = relative_source(inspect.getsourcefile(unwrapped) if unwrapped else None, legacy_root)
        try:
            view_source_line = inspect.getsourcelines(unwrapped)[1] if unwrapped is not None else None
        except (OSError, TypeError):
            view_source_line = None
        view_function = getattr(unwrapped, "__name__", None)
        function_fact = locate_function(
            functions_by_source,
            view_source,
            view_function,
            view_source_line,
        )
        renders = route_render_calls(functions_by_source, view_source, function_fact)
        rows.append(
            {
                "route_id": f"{'|'.join(methods)} {rule.rule} -> {rule.endpoint}",
                "path": rule.rule,
                "methods": methods,
                "endpoint": rule.endpoint,
                "source": source_ref(view_source, function_fact["start_line"] if function_fact else view_source_line),
                "source_path": view_source,
                "view_function": view_function,
                "render_templates": renders,
                "template_mapping_status": (
                    "literal_found"
                    if any(render["template"] is not None for render in renders)
                    else (
                        "candidate_literals_found"
                        if any(render["candidate_templates"] for render in renders)
                        else ("dynamic_only" if renders else "no_render_template_call_found")
                    )
                ),
            }
        )
    return rows


def template_module(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if len(parts) >= 3 and parts[:2] == ("app", "modules"):
        return parts[2]
    if relative_path.startswith("app/core/services/export/templates/"):
        return "core.services.export"
    if relative_path.startswith("app/core/utils/email_templates/"):
        return "core.utils.email_templates"
    return "app"


def template_name(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if "templates" in parts:
        index = parts.index("templates")
        return Path(*parts[index + 1 :]).as_posix()
    if relative_path.startswith("app/core/utils/email_templates/"):
        return Path(relative_path).name
    return Path(relative_path).name


def partial_convention(path: Path) -> list[str]:
    reasons: list[str] = []
    if path.stem.startswith("_") or any(part.startswith("_") for part in path.parts[:-1]):
        reasons.append("underscore_partial_convention")
    matched_directories = sorted(set(path.parts) & PARTIAL_DIRECTORIES)
    if matched_directories:
        reasons.append(f"partial_directory_convention:{','.join(matched_directories)}")
    if path.stem in LAYOUT_STEMS or path.stem.endswith("_base") or path.stem.endswith("_shell"):
        reasons.append("layout_or_shell_filename_convention")
    return reasons


def template_inventory(
    legacy_root: Path,
    render_calls: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    paths = sorted((legacy_root / "app").rglob("*.html"))
    names_to_paths: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        relative = path.relative_to(legacy_root).as_posix()
        names_to_paths[template_name(relative)].append(relative)

    static_references: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in render_calls:
        if call["template"] is not None:
            static_references[call["template"]].append(
                {
                    "source": call["source"],
                    "function": call["function"],
                }
            )

    route_references: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved_literals: set[str] = set()
    for route in routes:
        for render in route["render_templates"]:
            literals = [render["template"]] if render["template"] is not None else render["candidate_templates"]
            for literal in literals:
                candidates = names_to_paths.get(literal, [])
                if not candidates:
                    unresolved_literals.add(literal)
                    continue
                for candidate in candidates:
                    route_references[candidate].append(
                        {
                            "route_id": route["route_id"],
                            "path": route["path"],
                            "methods": route["methods"],
                            "endpoint": route["endpoint"],
                            "mapping_kind": render["mapping_kind"],
                            "template_resolution": (
                                "literal" if render["template"] is not None else "static_candidate"
                            ),
                            "render_source": render["source"],
                        }
                    )

    items: list[dict[str, Any]] = []
    for path in paths:
        relative = path.relative_to(legacy_root).as_posix()
        name = template_name(relative)
        route_refs = sorted(
            route_references.get(relative, []),
            key=lambda ref: (ref["path"], ref["methods"], ref["endpoint"], ref["render_source"]),
        )
        convention_reasons = partial_convention(Path(relative))
        if route_refs:
            classification = "page"
            basis = ["rendered_by_registered_runtime_route"]
        elif convention_reasons:
            classification = "partial"
            basis = convention_reasons
        else:
            classification = "page"
            basis = ["standalone_filename_without_partial_convention"]
        refs = sorted(
            static_references.get(name, []),
            key=lambda ref: (ref["source"], ref["function"] or ""),
        )
        items.append(
            {
                "module": template_module(relative),
                "relative_path": relative,
                "template_name": name,
                "classification": classification,
                "classification_basis": basis,
                "runtime_route_references": route_refs,
                "source_render_references": refs,
            }
        )
    return items, sorted(unresolved_literals)


def mini_program_pages(miniprogram_root: Path) -> list[dict[str, Any]]:
    config_path = miniprogram_root / "miniprogram" / "app.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    mini_root = config_path.parent
    tab_paths = {item["pagePath"] for item in data.get("tabBar", {}).get("list", [])}
    pages: list[dict[str, Any]] = []

    def implementation_files(full_path: str) -> list[str]:
        found: list[str] = []
        base = mini_root / full_path
        for suffix in (".ts", ".js", ".json", ".wxml", ".less", ".wxss"):
            candidate = base.with_suffix(suffix)
            if candidate.is_file():
                found.append(
                    (Path("miniprogram-1") / "miniprogram" / f"{full_path}{suffix}").as_posix()
                )
        return found

    def controlled_copy_files(full_path: str) -> list[str]:
        found: list[str] = []
        base = mini_root / full_path
        for suffix in (".ts", ".js", ".json", ".wxml", ".less", ".wxss"):
            candidate = base.with_suffix(suffix)
            if candidate.is_file():
                found.append((Path("Ti-Java/miniprogram/miniprogram") / f"{full_path}{suffix}").as_posix())
        return found

    for index, declared_path in enumerate(data.get("pages", [])):
        pages.append(
            {
                "package_kind": "main",
                "subpackage_root": None,
                "declared_path": declared_path,
                "full_path": declared_path,
                "declaration_source": f"miniprogram-1/miniprogram/app.json:pages[{index}]",
                "tab_bar_entry": declared_path in tab_paths,
                "implementation_files": implementation_files(declared_path),
                "controlled_copy_files": controlled_copy_files(declared_path),
            }
        )
    for package_index, package in enumerate(data.get("subPackages", [])):
        root = package["root"].strip("/")
        for page_index, declared_path in enumerate(package.get("pages", [])):
            full_path = f"{root}/{declared_path.strip('/')}"
            pages.append(
                {
                    "package_kind": "subpackage",
                    "subpackage_root": root,
                    "declared_path": declared_path,
                    "full_path": full_path,
                    "declaration_source": (
                        "miniprogram-1/miniprogram/app.json:"
                        f"subPackages[{package_index}].pages[{page_index}]"
                    ),
                    "tab_bar_entry": full_path in tab_paths,
                    "implementation_files": implementation_files(full_path),
                    "controlled_copy_files": controlled_copy_files(full_path),
                }
            )
    return pages


def mini_program_source_only_pages(
    miniprogram_root: Path,
    declared_pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find complete page-shaped source sets that app.json does not register."""
    mini_root = miniprogram_root / "miniprogram"
    declared_paths = {str(page["full_path"]) for page in declared_pages}
    searchable_suffixes = {".js", ".json", ".ts", ".wxml"}
    searchable_files = sorted(
        path for path in mini_root.rglob("*") if path.is_file() and path.suffix in searchable_suffixes
    )

    def files_for(full_path: str, prefix: str) -> list[str]:
        files: list[str] = []
        base = mini_root / full_path
        for suffix in (".ts", ".js", ".json", ".wxml", ".less", ".wxss"):
            if base.with_suffix(suffix).is_file():
                files.append(f"{prefix}/miniprogram/{full_path}{suffix}")
        return files

    rows: list[dict[str, Any]] = []
    for config_path in sorted(mini_root.rglob("*.json")):
        relative_config = config_path.relative_to(mini_root)
        full_path = relative_config.with_suffix("").as_posix()
        if (
            full_path in declared_paths
            or "_archived" in relative_config.parts
            or "components" in relative_config.parts
            or "custom-tab-bar" in relative_config.parts
            or "pages" not in relative_config.parts
        ):
            continue
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(config, dict) and config.get("component") is True:
            continue
        base = config_path.with_suffix("")
        if not base.with_suffix(".wxml").is_file() or not (
            base.with_suffix(".ts").is_file() or base.with_suffix(".js").is_file()
        ):
            continue

        references: list[str] = []
        for source_path in searchable_files:
            if source_path.parent == base.parent:
                continue
            try:
                lines = source_path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            for line_number, line in enumerate(lines, start=1):
                if full_path in line:
                    relative_source = source_path.relative_to(mini_root).as_posix()
                    references.append(
                        f"miniprogram-1/miniprogram/{relative_source}:{line_number}"
                    )

        rows.append(
            {
                "full_path": full_path,
                "declaration_status": "source_only_not_in_app_json",
                "classification_basis": (
                    "has page JSON, WXML, and TypeScript/JavaScript siblings; component is not true"
                ),
                "implementation_files": files_for(full_path, "miniprogram-1"),
                "controlled_copy_files": files_for(full_path, "Ti-Java/miniprogram"),
                "source_references": sorted(set(references)),
            }
        )
    return rows


def join_url_prefix(prefix: str, child: str) -> str:
    if child == "/":
        return f"{prefix.rstrip('/')}/"
    return f"{prefix.rstrip('/')}/{child.lstrip('/')}"


def decorator_methods(decorator: ast.Call) -> list[str]:
    for keyword in decorator.keywords:
        if keyword.arg != "methods":
            continue
        if isinstance(keyword.value, (ast.List, ast.Tuple, ast.Set)):
            methods = [literal_string(item) for item in keyword.value.elts]
            if all(method is not None for method in methods):
                return normalized_methods(method for method in methods if method is not None)
        return ["DYNAMIC"]
    return ["GET"]


def source_admin_declarations(legacy_root: Path, routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runtime_index: dict[tuple[str, str, str | None, str | None], list[str]] = defaultdict(list)
    for route in routes:
        for method in route["methods"]:
            runtime_index[(route["path"], method, route["source_path"], route["view_function"])].append(
                route["route_id"]
            )

    source_paths = sorted((legacy_root / "app" / "modules" / "admin" / "routes").rglob("*.py"))
    source_paths.append(legacy_root / "app" / "modules" / "coding" / "routes" / "admin.py")
    declarations: list[dict[str, Any]] = []
    for path in source_paths:
        source = path.relative_to(legacy_root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=source)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "route"
                    and isinstance(decorator.func.value, ast.Name)
                ):
                    continue
                blueprint_name = decorator.func.value.id
                prefix = ADMIN_BLUEPRINT_PREFIXES.get(blueprint_name)
                child = literal_string(decorator.args[0] if decorator.args else None)
                if prefix is None or child is None:
                    continue
                path_value = join_url_prefix(prefix, child)
                methods = decorator_methods(decorator)
                matches: list[str] = []
                for method in methods:
                    matches.extend(runtime_index.get((path_value, method, source, node.name), []))
                declarations.append(
                    {
                        "path": path_value,
                        "methods": methods,
                        "function": node.name,
                        "blueprint": blueprint_name,
                        "entry_kind": (
                            "web"
                            if blueprint_name == "admin_pages_bp"
                            or (blueprint_name == "coding_admin_bp" and not child.startswith("/api"))
                            else "api"
                        ),
                        "source": source_ref(source, decorator.lineno),
                        "registered": bool(matches),
                        "runtime_route_ids": sorted(set(matches)),
                    }
                )
    return sorted(
        declarations,
        key=lambda row: (row["path"], row["methods"], row["source"], row["function"]),
    )


def admin_inventory(routes: list[dict[str, Any]], declarations: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for route in routes:
        if not (route["path"] == "/admin" or route["path"].startswith("/admin/")):
            continue
        has_literal_template = any(render["template"] is not None for render in route["render_templates"])
        entry_kind = "web" if route["methods"] == ["GET"] and has_literal_template else "api"
        entries.append(
            {
                "route_id": route["route_id"],
                "path": route["path"],
                "methods": route["methods"],
                "endpoint": route["endpoint"],
                "entry_kind": entry_kind,
                "classification_basis": (
                    "GET route with a literal render_template target"
                    if entry_kind == "web"
                    else "non-page method or no literal render_template target"
                ),
                "source": route["source"],
                "render_templates": route["render_templates"],
            }
        )
    source_only = [declaration for declaration in declarations if not declaration["registered"]]
    counts = Counter(entry["entry_kind"] for entry in entries)
    return {
        "runtime_entry_count": len(entries),
        "runtime_web_entry_count": counts["web"],
        "runtime_api_entry_count": counts["api"],
        "runtime_entries": entries,
        "source_declaration_count": len(declarations),
        "source_only_declaration_count": len(source_only),
        "source_declared_entries": declarations,
        "source_only_entries": source_only,
    }


def build_journeys(routes: list[dict[str, Any]], mini_pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    route_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for route in routes:
        for method in route["methods"]:
            route_index[(method, route["path"])].append(route)
    mini_index = {page["full_path"]: page for page in mini_pages}

    journeys: list[dict[str, Any]] = []
    for journey_id, name, route_specs, mini_specs in JOURNEY_DEFINITIONS:
        evidence: list[dict[str, Any]] = []
        for surface, method, path in route_specs:
            matches = route_index.get((method, path), [])
            if not matches:
                raise RuntimeError(f"Journey {journey_id} references missing route: {method} {path}")
            for match in matches:
                evidence.append(
                    {
                        "surface": surface,
                        "path": path,
                        "method": method,
                        "endpoint": match["endpoint"],
                        "source": match["source"],
                    }
                )
        for full_path in mini_specs:
            page = mini_index.get(full_path)
            if page is None:
                raise RuntimeError(f"Journey {journey_id} references missing mini page: {full_path}")
            evidence.append(
                {
                    "surface": "miniprogram",
                    "path": full_path,
                    "declaration_source": page["declaration_source"],
                }
            )
        journeys.append({"journey_id": journey_id, "name": name, "evidence": evidence})
    return journeys


def build_inventory(legacy_root: Path, miniprogram_root: Path) -> dict[str, Any]:
    functions_by_source, render_calls = analyze_python_sources(legacy_root)

    with tempfile.TemporaryDirectory(prefix="ti-java-surfaces-") as data_dir:
        data_path = Path(data_dir)
        database_path = data_path / "instance" / "surfaces.db"
        os.environ["DATA_DIR"] = str(data_path)
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["FLASK_ENV"] = "testing"
        os.environ["RATELIMIT_STORAGE_URI"] = "memory://"
        os.environ["RATELIMIT_STORAGE_URL"] = "memory://"
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ.pop("REDIS_URL", None)
        os.environ.pop("TI_BACKUP_SCHEDULER", None)
        sys.path.insert(0, str(legacy_root))
        previous_cwd = Path.cwd()
        try:
            os.chdir(legacy_root)
            logging.disable(logging.CRITICAL)
            import app as legacy_app

            legacy_app._start_background_tasks = lambda _app: None
            app = legacy_app.create_app("testing")
            routes = runtime_routes(app, legacy_root, functions_by_source)
        finally:
            os.chdir(previous_cwd)

    templates, unresolved_literals = template_inventory(legacy_root, render_calls, routes)
    mini_pages = mini_program_pages(miniprogram_root)
    mini_source_only_pages = mini_program_source_only_pages(miniprogram_root, mini_pages)
    admin_declarations = source_admin_declarations(legacy_root, routes)
    admin = admin_inventory(routes, admin_declarations)
    journeys = build_journeys(routes, mini_pages)

    template_counts = Counter(item["classification"] for item in templates)
    mini_counts = Counter(item["package_kind"] for item in mini_pages)
    route_mapping_counts = Counter(route["template_mapping_status"] for route in routes)
    source_literal_count = sum(1 for call in render_calls if call["template"] is not None)
    source_dynamic_count = len(render_calls) - source_literal_count

    if len(templates) != 309:
        raise RuntimeError(f"Expected 309 legacy HTML templates, found {len(templates)}")
    if len(mini_pages) != 61 or mini_counts != {"main": 50, "subpackage": 11}:
        raise RuntimeError(f"Expected 50 main + 11 subpackage pages, found {dict(mini_counts)}")
    if any(not page["implementation_files"] for page in mini_pages):
        missing = [page["full_path"] for page in mini_pages if not page["implementation_files"]]
        raise RuntimeError(f"Declared mini pages lack implementation files: {missing}")
    if len(mini_source_only_pages) != 7:
        raise RuntimeError(
            "Expected 7 complete source-only mini-program pages, found "
            f"{len(mini_source_only_pages)}"
        )
    if admin["source_only_declaration_count"] != 7:
        raise RuntimeError(
            "Expected 7 source-only admin popup declarations, found "
            f"{admin['source_only_declaration_count']}"
        )

    return {
        "schema_version": 1,
        "purpose": "Phase-0 client, page, template, and admin-entry baseline for the Ti Java migration.",
        "legacy_commit": LEGACY_BASELINE_COMMIT,
        "inputs": {
            "legacy_baseline": ".",
            "miniprogram_controlled_copy": "Ti-Java/miniprogram",
            "miniprogram_original_source": "miniprogram-1",
        },
        "safety": {
            "runtime_import": "Flask testing app imported only for url_map inspection",
            "data_dir": "ephemeral tempfile",
            "database": "explicit ephemeral SQLite URL; no schema creation or request execution",
            "background_tasks": "app._start_background_tasks replaced with a no-op before create_app",
            "bytecode": "sys.dont_write_bytecode and PYTHONDONTWRITEBYTECODE enabled",
            "miniprogram": "read only from the phase-0 controlled copy; evidence paths retain the original source prefix",
        },
        "summary": {
            "html_template_count": len(templates),
            "html_page_heuristic_count": template_counts["page"],
            "html_partial_heuristic_count": template_counts["partial"],
            "runtime_route_rule_count": len(routes),
            "runtime_expanded_method_count": sum(len(route["methods"]) for route in routes),
            "runtime_route_template_mapping_status": dict(sorted(route_mapping_counts.items())),
            "source_render_template_call_count": len(render_calls),
            "source_literal_render_template_call_count": source_literal_count,
            "source_dynamic_render_template_call_count": source_dynamic_count,
            "miniprogram_declared_page_count": len(mini_pages),
            "miniprogram_main_page_count": mini_counts["main"],
            "miniprogram_subpackage_page_count": mini_counts["subpackage"],
            "miniprogram_source_only_page_count": len(mini_source_only_pages),
            "admin_runtime_entry_count": admin["runtime_entry_count"],
            "admin_source_only_entry_count": admin["source_only_declaration_count"],
            "journey_count": len(journeys),
        },
        "template_classification_heuristic": {
            "page": (
                "A registered runtime route renders the template, or its path/name has no partial/layout convention."
            ),
            "partial": (
                "The basename/ancestor uses an underscore, a known partial directory, or a base/shell layout name, "
                "unless a registered runtime route renders it directly."
            ),
            "caveat": "This is a migration heuristic, not proof that an unregistered standalone page is reachable.",
        },
        "templates": templates,
        "source_render_template_calls": render_calls,
        "runtime_routes": routes,
        "unresolved_runtime_template_literals": unresolved_literals,
        "miniprogram_pages": mini_pages,
        "miniprogram_source_only_pages": mini_source_only_pages,
        "admin_entries": admin,
        "key_journeys": journeys,
    }


def main() -> int:
    args = parse_args()
    legacy_root = args.legacy_root.resolve()
    miniprogram_root = args.miniprogram_root.resolve()
    output = args.output.resolve()
    if not (legacy_root / "app" / "__init__.py").is_file():
        raise SystemExit(f"Not a Ti legacy root: {legacy_root}")
    if not (miniprogram_root / "miniprogram" / "app.json").is_file():
        raise SystemExit(f"Missing controlled mini-program app.json under: {miniprogram_root}")
    try:
        miniprogram_relative = miniprogram_root.relative_to(legacy_root).as_posix()
    except ValueError as exc:
        raise SystemExit("--miniprogram-root must be inside --legacy-root") from exc
    if miniprogram_relative != "Ti-Java/miniprogram":
        raise SystemExit(
            "--miniprogram-root must be the phase-0 controlled copy at Ti-Java/miniprogram; "
            f"received {miniprogram_relative}"
        )

    inventory = build_inventory(legacy_root, miniprogram_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "surface inventory: "
        f"templates={inventory['summary']['html_template_count']} "
        f"routes={inventory['summary']['runtime_route_rule_count']} "
        f"mini_pages={inventory['summary']['miniprogram_declared_page_count']} "
        f"admin_entries={inventory['summary']['admin_runtime_entry_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
