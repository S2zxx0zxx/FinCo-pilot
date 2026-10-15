"""Offline AST route inventory. Explicit dependencies are review leads, not auth proof."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def inventory(root: Path = ROOT) -> list[dict]:
    rows = []
    for base in (root / 'backend/app/api', root / 'backend/app/agents/api'):
        for path in sorted(base.glob('*.py')):
            tree = ast.parse(path.read_text())
            prefixes = {}
            for node in tree.body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    call = node.value
                    if ast.unparse(call.func) == 'APIRouter':
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                prefixes[target.id] = next((ast.literal_eval(k.value) for k in call.keywords if k.arg == 'prefix'), '')
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                deps = sorted({ast.unparse(n) for n in ast.walk(node.args) if isinstance(n, ast.Call) and ast.unparse(n.func) == 'Depends'})
                for dec in node.decorator_list:
                    if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
                        continue
                    if dec.func.attr not in {'get', 'post', 'put', 'patch', 'delete', 'websocket'}:
                        continue
                    url = ast.literal_eval(dec.args[0]) if dec.args else ''
                    rows.append({'method': dec.func.attr.upper(), 'path': prefixes.get(ast.unparse(dec.func.value), '') + url,
                                 'handler': node.name, 'source': str(path.relative_to(root)), 'line': node.lineno,
                                 'explicit_dependencies': deps,
                                 'decorator_dependencies': [ast.unparse(k.value) for k in dec.keywords if k.arg == 'dependencies'],
                                 'effective_permission': 'REVIEW_REQUIRED'})
    return rows



def runtime_inventory() -> dict:
    """Build schema/dependency evidence only in a fresh synthetic subprocess.

    No lifespan/startup, database queries or real provider calls are executed.
    Deployment env/secrets are deliberately not inherited.
    """
    import os
    import subprocess
    import sys
    import tempfile

    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
    env["PYTHONPATH"] = str(ROOT / "backend")
    env["FINCO_INVENTORY_ROOT"] = str(ROOT)
    env["CREDENTIALS_DIRECTORY"] = ""
    env["SENTRY_ENABLED"] = "false"
    code = r"""
from app.core.config import Settings
# Settings anchors .env to the checkout; disabling it is required even in a fresh cwd.
Settings.model_config = {**Settings.model_config, "env_file": None}
import tests.conftest
import inspect, json, os, re
from pathlib import Path
from fastapi.routing import APIRoute
from app.main import app
from tests.test_write_permission_coverage import _dependency_names, ALLOWLIST
root = Path(os.environ["FINCO_INVENTORY_ROOT"])
rows = []
def walk(routes, prefix='', parent_deps=()):
    for route in routes:
        if hasattr(route, 'original_router'):
            ctx = route.include_context
            walk(route.original_router.routes, prefix + ctx.prefix, parent_deps + tuple(ctx.dependencies))
        elif isinstance(route, APIRoute):
            names = _dependency_names(route) | {getattr(d.dependency, '__name__', type(d.dependency).__name__) for d in parent_deps}
            names = {re.sub(r' at 0x[0-9a-fA-F]+', '', name) for name in names}
            path = Path(inspect.getfile(route.endpoint))
            for method in sorted(route.methods):
                policy = ALLOWLIST.get((method, route.path))
                category = ('workspace-write' if 'current_writable_workspace' in names else 'workspace-read' if 'current_workspace' in names else 'review-explicit-policy' if policy else 'review-handler-policy')
                rows.append({'method': method, 'path': prefix + route.path,
                    'source': str(path.relative_to(root)) if path.is_relative_to(root) else 'generated-library-route',
                    'handler': route.endpoint.__name__, 'dependency_names': sorted(names),
                    'permission_category': category, 'explicit_policy': policy, 'service_ownership_tests_required': True})
walk(app.routes)
operations = []
for path, methods in app.openapi()['paths'].items():
    for method, op in methods.items():
        if method in {'get', 'post', 'put', 'patch', 'delete'}:
            operations.append({'path': path, 'method': method.upper(), 'operation': op.get('operationId'),
                'security': op.get('security', []), 'tags': op.get('tags', []),
                'authorization_result': 'Schema declaration only; service-level A/B tests required'})
print(json.dumps({'runtime_routes': rows, 'openapi_operations': operations}))
"""
    # Fresh cwd avoids incidental relative storage; anchored .env is disabled above.
    with tempfile.TemporaryDirectory(prefix="finco-route-inventory-") as directory:
        result = subprocess.run([sys.executable, "-c", code], env=env, cwd=directory,
                                check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', action='store_true', help='Fresh synthetic test-environment schema and dependency graph; no startup')
    args = parser.parse_args()
    result = runtime_inventory() if args.runtime else {
        'scope': 'AST only; main.py mounts and generated fastapi-users/MCP routes require separate review',
        'routes': inventory(),
    }
    print(json.dumps(result, indent=2))
