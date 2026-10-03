from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_cloudflare_edge_compose_is_secret_file_based_and_origin_is_not_public():
    compose = _read("docker-compose.prod.yml")

    assert 'profiles: ["cloudflare-edge"]' in compose
    assert "cloudflare/cloudflared:${CLOUDFLARED_VERSION:-2026.9.3}" in compose
    assert "--token-file" in compose
    assert "/run/secrets/cloudflare_tunnel_token" in compose
    assert "CLOUDFLARE_TUNNEL_TOKEN:" not in compose
    assert '"127.0.0.1:${FRONTEND_PORT:-3000}:8080"' in compose
    assert '"127.0.0.1:${BACKEND_PORT:-8000}:8000"' in compose


def test_frontend_proxy_preserves_edge_https_scheme_in_compose_and_helm():
    compose_nginx = _read("frontend/default.conf.template")
    helm_nginx = _read("charts/fincopilot/templates/frontend/configmap-nginx.yaml")

    for config in (compose_nginx, helm_nginx):
        assert "map $http_x_forwarded_proto $finco_forwarded_proto" in config
        assert "https https;" in config
        assert "proxy_set_header X-Forwarded-Proto $finco_forwarded_proto;" in config
        assert "proxy_set_header X-Forwarded-Proto $scheme;" not in config


def test_cloudflare_edge_operator_runbook_keeps_compute_and_r2_separate():
    runbook = _read("docs/trust/FINCO_CLOUDFLARE_EDGE_V1.md")

    assert "fincopilot-origin" in runbook
    assert "https://fincopilot.satzzxzxx.me" in runbook
    assert "TRUSTED_PROXY_HOPS=2" in runbook
    assert "fincopilot-prod" in runbook
    assert "does not by itself close" in runbook
