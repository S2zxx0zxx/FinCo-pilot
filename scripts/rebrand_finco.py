from __future__ import annotations

from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
WORKFLOW = ROOT / ".github" / "workflows" / "rebrand-finco.yml"

REPO_WEB = "https://github.com/S2zxx0zxx/FinCo-pilot"
REPO_API = "https://api.github.com/repos/S2zxx0zxx/FinCo-pilot"

# Order matters: replace specific external identities/URLs before generic brand tokens.
REPLACEMENTS: list[tuple[str, str]] = [
    ("https://api.github.com/repos/securo-finance/securo", REPO_API),
    ("https://raw.githubusercontent.com/securo-finance/securo", "https://raw.githubusercontent.com/S2zxx0zxx/FinCo-pilot"),
    ("https://github.com/securo-finance/securo.git", REPO_WEB + ".git"),
    ("https://github.com/securo-finance/securo-docs", REPO_WEB),
    ("https://github.com/securo-finance/securo", REPO_WEB),
    ("ghcr.io/securo-finance/securo-backend", "ghcr.io/s2zxx0zxx/fincopilot-backend"),
    ("ghcr.io/securo-finance/securo-frontend", "ghcr.io/s2zxx0zxx/fincopilot-frontend"),
    ("securo-finance/securo-docs", "S2zxx0zxx/FinCo-pilot"),
    ("securo-finance/securo", "S2zxx0zxx/FinCo-pilot"),
    ("securo-finance", "S2zxx0zxx"),
    ("https://usesecuro.com/install.sh", "https://raw.githubusercontent.com/S2zxx0zxx/FinCo-pilot/main/install.sh"),
    ("https://demo.usesecuro.com/", REPO_WEB + "#quick-start"),
    ("https://demo.usesecuro.com", REPO_WEB + "#quick-start"),
    ("https://www.usesecuro.com/roadmap", REPO_WEB + "/issues"),
    ("https://docs.usesecuro.com/", REPO_WEB + "#readme"),
    ("https://docs.usesecuro.com", REPO_WEB + "#readme"),
    ("https://usesecuro.com/", REPO_WEB),
    ("https://usesecuro.com", REPO_WEB),
    ("info@usesecuro.com", "private security advisory"),
    ("https://cal.com/tassio/15min", REPO_WEB + "/issues"),
    ("https://discord.gg/rUqTKtQ9S4", REPO_WEB),
    ("tassionoronha", "S2zxx0zxx"),
    ("tassio@example.com", "user@example.com"),
    ("TASSIO", "PRIMARY"),
    ("Tassio", "Primary"),
    ("tassio", "user"),
    ("ShellLogo", "FinCoLogo"),
    ("@/components/shell-logo", "@/components/finco-logo"),
    ("shell-logo", "finco-logo"),
    ("Securo", "FinCo-Pilot"),
    ("SECURO", "FINCOPILOT"),
    ("securo", "fincopilot"),
]

LEGACY_PATTERNS = [
    re.compile(r"securo", re.I),
    re.compile(r"usesecuro", re.I),
    re.compile(r"securo-finance", re.I),
    re.compile(r"tassionoronha", re.I),
    re.compile(r"\btassio\b", re.I),
    re.compile(r"rUqTKtQ9S4"),
    re.compile(r"ae627b744aaa2ba89d850ea541c311be", re.I),
    re.compile(r"shell-logo", re.I),
    re.compile(r"ShellLogo"),
]

SKIP_EXACT = {
    ROOT / "LICENSE",  # User explicitly asked to leave the legal license unchanged.
    SELF,
    WORKFLOW,
}


def is_text_file(path: Path) -> bool:
    try:
        raw = path.read_bytes()
    except OSError:
        return False
    if b"\x00" in raw:
        return False
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def replace_text_everywhere() -> int:
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path in SKIP_EXACT:
            continue
        if not is_text_file(path):
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1
    return changed


def rename_legacy_paths() -> list[tuple[str, str]]:
    renamed: list[tuple[str, str]] = []

    # Rename component to make the new visual identity explicit in the codebase.
    pairs = [
        (ROOT / "frontend/src/components/shell-logo.tsx", ROOT / "frontend/src/components/finco-logo.tsx"),
        (ROOT / "frontend/src/components/shell-logo.test.tsx", ROOT / "frontend/src/components/finco-logo.test.tsx"),
        (ROOT / "charts/securo", ROOT / "charts/fincopilot"),
    ]
    for src, dst in pairs:
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            renamed.append((str(src.relative_to(ROOT)), str(dst.relative_to(ROOT))))

    # Defensive pass: no remaining filename or directory should expose the old product name.
    candidates = sorted(
        [p for p in ROOT.rglob("*") if ".git" not in p.parts and p not in {SELF, WORKFLOW}],
        key=lambda p: len(p.parts),
        reverse=True,
    )
    for path in candidates:
        if not path.exists():
            continue
        new_name = re.sub("securo", "fincopilot", path.name, flags=re.I)
        if new_name == path.name:
            continue
        dst = path.with_name(new_name)
        if not dst.exists():
            path.rename(dst)
            renamed.append((str(path.relative_to(ROOT)), str(dst.relative_to(ROOT))))
    return renamed


FINCO_LOGO_TSX = """type FinCoLogoProps = {
  size?: number
  className?: string
}

/** FinCo-Pilot mark: a rising finance path ending in a pilot beacon. */
export function FinCoLogo({ size = 24, className }: FinCoLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox=\"0 0 32 32\"
      preserveAspectRatio=\"xMidYMid meet\"
      className={className}
      fill=\"none\"
      xmlns=\"http://www.w3.org/2000/svg\"
      aria-hidden=\"true\"
    >
      <path
        d=\"M5 24V18.5M11 24V14M17 24V17M23 24V10\"
        stroke=\"currentColor\"
        strokeWidth=\"2.6\"
        strokeLinecap=\"round\"
        opacity=\"0.42\"
      />
      <path
        d=\"M5 18.5L11 13.5L17 17L25.5 7.5\"
        stroke=\"currentColor\"
        strokeWidth=\"2.8\"
        strokeLinecap=\"round\"
        strokeLinejoin=\"round\"
      />
      <circle cx=\"25.5\" cy=\"7.5\" r=\"3.1\" fill=\"currentColor\" />
      <circle cx=\"25.5\" cy=\"7.5\" r=\"1.1\" fill=\"white\" fillOpacity=\"0.9\" />
    </svg>
  )
}
"""

FINCO_LOGO_TEST = """import { describe, expect, it } from 'vitest'

import { FinCoLogo } from '@/components/finco-logo'
import { renderWithProviders } from '@/test/utils'

describe('FinCoLogo', () => {
  it('renders an svg at the default size', () => {
    const { container } = renderWithProviders(<FinCoLogo />)
    const svg = container.querySelector('svg')!
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('width', '24')
    expect(svg).toHaveAttribute('height', '24')
  })

  it('honours an explicit size on both axes', () => {
    const { container } = renderWithProviders(<FinCoLogo size={64} />)
    const svg = container.querySelector('svg')!
    expect(svg).toHaveAttribute('width', '64')
    expect(svg).toHaveAttribute('height', '64')
  })

  it('keeps a fixed viewBox so the mark never distorts', () => {
    const { container } = renderWithProviders(<FinCoLogo size={120} />)
    const svg = container.querySelector('svg')!
    expect(svg).toHaveAttribute('viewBox', '0 0 32 32')
    expect(svg).toHaveAttribute('preserveAspectRatio', 'xMidYMid meet')
  })

  it('uses currentColor so it follows the theme', () => {
    const { container } = renderWithProviders(<FinCoLogo />)
    expect(container.querySelector('path')).toHaveAttribute('stroke', 'currentColor')
  })

  it('accepts a className', () => {
    const { container } = renderWithProviders(<FinCoLogo className=\"text-primary\" />)
    expect(container.querySelector('svg')).toHaveClass('text-primary')
  })
})
"""

DOCS_LOGO = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 520 160\" role=\"img\" aria-labelledby=\"title desc\">
  <title id=\"title\">FinCo-Pilot</title>
  <desc id=\"desc\">FinCo-Pilot finance path and beacon mark</desc>
  <rect width=\"520\" height=\"160\" rx=\"32\" fill=\"#0B0B0F\"/>
  <g transform=\"translate(34 34)\" fill=\"none\" stroke=\"#FF7A59\" stroke-linecap=\"round\" stroke-linejoin=\"round\">
    <path d=\"M4 76V58M24 76V42M44 76V52M64 76V26\" stroke-width=\"8\" opacity=\".38\"/>
    <path d=\"M4 58L24 40L44 52L75 16\" stroke-width=\"9\"/>
    <circle cx=\"75\" cy=\"16\" r=\"10\" fill=\"#FF7A59\" stroke=\"none\"/>
    <circle cx=\"75\" cy=\"16\" r=\"3.5\" fill=\"#FFF4EE\" stroke=\"none\"/>
  </g>
  <text x=\"142\" y=\"94\" fill=\"#F7F7FA\" font-family=\"Inter, Geist, Arial, sans-serif\" font-size=\"50\" font-weight=\"700\" letter-spacing=\"-1.5\">FinCo-Pilot</text>
</svg>
"""

README = """<p align=\"center\">
  <img src=\"docs/logo.svg\" width=\"260\" alt=\"FinCo-Pilot logo\" />
</p>
<h1 align=\"center\">FinCo-Pilot</h1>
<p align=\"center\">
  <a href=\"https://github.com/S2zxx0zxx/FinCo-pilot/actions/workflows/ci.yml\"><img src=\"https://github.com/S2zxx0zxx/FinCo-pilot/actions/workflows/ci.yml/badge.svg\" alt=\"CI\" /></a>
  <a href=\"https://www.gnu.org/licenses/agpl-3.0\"><img src=\"https://img.shields.io/badge/License-AGPL--3.0-blue.svg\" alt=\"License: AGPL-3.0\" /></a>
</p>

<h3 align=\"center\">Your finances, one intelligent cockpit.</h3>

FinCo-Pilot is a privacy-first personal finance platform for managing accounts, transactions, budgets, goals, assets, invoices, shared expenses, reports, bank connections, and optional AI agents from one workspace. It is designed to keep financial data under the operator's control while providing a fast, modern web experience.

## Quick Start

**Linux & macOS** (Docker or Podman):

```bash
curl -fsSL https://raw.githubusercontent.com/S2zxx0zxx/FinCo-pilot/main/install.sh | bash
```

**Windows:** install Docker Desktop, then:

```bash
git clone https://github.com/S2zxx0zxx/FinCo-pilot.git
cd FinCo-pilot
docker compose up --build
```

Open `http://localhost:3000` and create an account.

<p align=\"center\">
  <img src=\"docs/screenshot.png\" width=\"800\" alt=\"FinCo-Pilot dashboard\" />
</p>

## Features

- Multi-account management with running balances and account reconciliation
- Transaction management with search, filters, splits, attachments, payees, and CSV export
- File imports for OFX, QIF, CAMT, CSV, and investment data
- Automatic categorization rules and reusable collections
- Recurring transactions, budgets, goals, and savings tracking
- Asset management with valuation history, transactions, grouping, and market-price support
- Net-worth, cash-flow, income/expense, and category reporting
- Shared groups, settlements, and workspace-level collaboration
- Invoice creation, attachments, PDF generation, sharing, and forecasting
- Multi-currency support with automatic FX conversion
- Optional bank synchronization through Pluggy, Enable Banking, and SimpleFIN
- Multi-user administration with workspace roles and registration controls
- TOTP two-factor authentication, passkeys/WebAuthn, and brute-force protections
- OIDC/SSO support for standard OpenID Connect providers
- Optional AI agents with multiple LLM providers, MCP tool access, and per-agent RAG knowledge bases
- Backup and restore, including optional AES-256 encrypted archives

## Bank Sync (Optional)

Configure any provider you use in `.env`, then restart the stack.

### Pluggy

```env
PLUGGY_CLIENT_ID=your-client-id
PLUGGY_CLIENT_SECRET=your-client-secret
```

### Enable Banking

```env
ENABLE_BANKING_APP_ID=your-application-id
ENABLE_BANKING_PRIVATE_KEY_FILE=/app/secrets/your-key.pem
ENABLE_BANKING_OAUTH_REDIRECT_URI=https://your-host/oauth/callback
```

### SimpleFIN

```env
SIMPLEFIN_ENABLED=true
SIMPLEFIN_API_URL=https://beta-bridge.simplefin.org
```

## Authentication and SSO

Local authentication is enabled by default. To delegate login to an OIDC provider:

```env
OIDC_ENABLED=true
OIDC_PROVIDER_NAME=Your Provider
OIDC_DISCOVERY_URL=https://id.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=fincopilot
OIDC_CLIENT_SECRET=your-client-secret
OIDC_REDIRECT_URI=https://your-finco-host/api/auth/oidc/callback
```

Set `LOCAL_AUTH_ENABLED=false` only after OIDC is fully configured and an administrator can sign in through the provider. Optional role synchronization is controlled by `OIDC_SYNC_ROLES`, `OIDC_ROLES_CLAIM`, `OIDC_ADMIN_ROLES`, and `OIDC_WORKSPACE_ROLE_MAP`.

## Passkeys

Passkeys work on `http://localhost:3000` or on an HTTPS domain. For a deployed domain, set:

```env
FRONTEND_URL=https://finance.example.com
WEBAUTHN_RP_ID=finance.example.com
```

## Exchange Rates

For automatic exchange-rate lookup:

```env
OPENEXCHANGERATES_APP_ID=your-app-id
```

Without a key, foreign-currency transactions continue to work with the application's fallback behavior.

## AI Agents (Optional)

AI features are opt-in and off by default.

```env
AGENTS_ENABLED=true
COMPOSE_PROFILES=agents
```

Then start the stack with `docker compose up -d`. Provider connections are configured from **Settings → AI Agents**. Supported integrations include OpenAI, Anthropic, Ollama, and OpenAI-compatible endpoints. The built-in MCP server can expose approved finance tools to agent workflows.

For a non-Docker installation, run the MCP service separately:

```bash
uvicorn mcp_server.main:app --host 127.0.0.1 --port 8765
```

and configure:

```env
AGENTS_BUILTIN_MCP_URL=http://127.0.0.1:8765/mcp
```

## Tech Stack

| Layer | Stack |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic, Celery |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Database | PostgreSQL + pgvector |
| Queue | Redis + Celery |
| AI tooling | MCP, provider adapters, RAG/embeddings |

## Development

```bash
cd backend
pip install -e \".[dev]\"
pytest
```

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm test
```

Or use the repository's `mise` tasks for installation, linting, tests, and builds.

## Security

Please report vulnerabilities privately through GitHub Security Advisories for this repository. See [SECURITY.md](SECURITY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and contribution guidelines.

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).
"""

SECURITY = """# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in FinCo-Pilot, please report it responsibly and **do not open a public issue containing exploit details or sensitive information**.

Use GitHub's private vulnerability reporting / Security Advisories for this repository:

https://github.com/S2zxx0zxx/FinCo-pilot/security/advisories/new

Please include:

- the affected component and version or commit
- reproduction steps or a proof of concept
- the security impact you observed
- any suggested mitigation, if known

We will review credible reports as quickly as practical and coordinate remediation before public disclosure.

## Supported versions

Security fixes target the current maintained release line. Operators should keep FinCo-Pilot and its dependencies up to date and rotate credentials if exposure is suspected.
"""

DOWNLOADS_WORKFLOW = """name: Downloads Badge Data

on:
  schedule:
    - cron: '17 5 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update-badge-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Fetch GHCR download counts
        shell: bash
        run: |
          count() {
            curl -sfL \"https://github.com/S2zxx0zxx/FinCo-pilot/pkgs/container/$1\" \\
              | grep -A1 'Total downloads' \\
              | grep -oE 'title=\"[0-9]+\"' \\
              | grep -oE '[0-9]+' || true
          }
          backend=$(count fincopilot-backend)
          frontend=$(count fincopilot-frontend)
          backend=${backend:-0}
          frontend=${frontend:-0}
          min=$(( backend < frontend ? backend : frontend ))
          mkdir -p badges
          printf '{\"schemaVersion\":1,\"label\":\"downloads\",\"message\":\"%s\",\"color\":\"orange\"}\n' \"$min\" > badges/downloads.json
      - name: Commit badge data when changed
        run: |
          if git diff --quiet -- badges/downloads.json; then exit 0; fi
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add badges/downloads.json
          git commit -m 'chore: refresh download badge data'
          git push
"""


def write_curated_files() -> None:
    (ROOT / "README.md").write_text(README, encoding="utf-8")
    (ROOT / "SECURITY.md").write_text(SECURITY, encoding="utf-8")
    (ROOT / "docs/logo.svg").write_text(DOCS_LOGO, encoding="utf-8")
    (ROOT / "frontend/src/components/finco-logo.tsx").write_text(FINCO_LOGO_TSX, encoding="utf-8")
    (ROOT / "frontend/src/components/finco-logo.test.tsx").write_text(FINCO_LOGO_TEST, encoding="utf-8")
    (ROOT / ".github/workflows/downloads-badge.yml").write_text(DOWNLOADS_WORKFLOW, encoding="utf-8")

    badges = ROOT / "badges"
    badges.mkdir(exist_ok=True)
    (badges / "downloads.json").write_text(
        '{"schemaVersion":1,"label":"downloads","message":"0","color":"orange"}\n',
        encoding="utf-8",
    )


def update_brand_palette() -> None:
    css = ROOT / "frontend/src/index.css"
    if css.exists():
        text = css.read_text(encoding="utf-8")
        color_map = {
            "#6366F1": "#F97316",
            "#4F46E5": "#C2410C",
            "#EEF2FF": "#FFF1E8",
            "#8B5CF6": "#FB7185",
            "#818CF8": "#FB7A5B",
            "#1E1B4B": "#3A1F18",
            "#A5B4FC": "#FDBA9A",
            "#a78bfa": "#fb923c",
            "#c4b5fd": "#fdba74",
            "#818cf8": "#fb7185",
        }
        for old, new in color_map.items():
            text = text.replace(old, new)
        text = text.replace(
            "Soft ambient aurora for the auth brand panel. Drifting, blurred purple\n   blobs over a deep indigo base",
            "Soft ambient glow for the FinCo-Pilot auth panel. Warm coral and amber\n   light over a graphite base",
        )
        css.write_text(text, encoding="utf-8")

    auth = ROOT / "frontend/src/components/auth-brand-panel.tsx"
    if auth.exists():
        text = auth.read_text(encoding="utf-8")
        text = text.replace(
            "'linear-gradient(150deg, #3F37C9 0%, #5B30C9 48%, #6D28D9 100%)'",
            "'linear-gradient(150deg, #0B0B0F 0%, #171217 52%, #2B1711 100%)'",
        )
        text = text.replace("deep indigo→violet", "graphite→warm-coral")
        text = text.replace("translucent\n// shell watermark", "translucent\n// FinCo-Pilot watermark")
        auth.write_text(text, encoding="utf-8")


def update_ci_badge_publishing() -> None:
    ci = ROOT / ".github/workflows/ci.yml"
    if not ci.exists():
        return
    text = ci.read_text(encoding="utf-8")
    # Remove the old external gist publishing step while keeping all CI/test/coverage jobs.
    text = re.sub(
        r"\n\s*- name: Update coverage badge.*?(?=\n\s*- name:|\n\s{0,4}[A-Za-z0-9_-]+:|\Z)",
        "\n",
        text,
        flags=re.S,
    )
    # Any surviving hard-coded gist ownership/token references are obsolete for this repo.
    text = re.sub(r"(?ms)^.*GIST_TOKEN.*\n?", "", text)
    text = re.sub(r"(?ms)^.*ae627b744aaa2ba89d850ea541c311be.*\n?", "", text)
    ci.write_text(text, encoding="utf-8")


def regenerate_brand_images() -> None:
    from PIL import Image, ImageDraw, ImageFont

    def font(size: int, bold: bool = False):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size=size)
        return ImageFont.load_default()

    def icon(size: int) -> Image.Image:
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        m = max(1, size // 12)
        d.rounded_rectangle((m, m, size - m, size - m), radius=max(2, size // 5), fill=(11, 11, 15, 255))
        coral = (255, 122, 89, 255)
        muted = (255, 122, 89, 105)
        pts = [
            (int(size * 0.20), int(size * 0.66)),
            (int(size * 0.38), int(size * 0.47)),
            (int(size * 0.55), int(size * 0.57)),
            (int(size * 0.76), int(size * 0.30)),
        ]
        width = max(2, size // 14)
        for x, y in pts[:-1]:
            d.line((x, int(size * 0.72), x, y), fill=muted, width=width)
        d.line(pts, fill=coral, width=width, joint="curve")
        r = max(2, size // 13)
        x, y = pts[-1]
        d.ellipse((x-r, y-r, x+r, y+r), fill=coral)
        return im

    # Brand every favicon in both canonical asset locations.
    for base in [ROOT / "favicons", ROOT / "frontend/public"]:
        if not base.exists():
            continue
        for path in base.glob("*.png"):
            m = re.search(r"(\d+)x(\d+)", path.name)
            if m:
                w, h = int(m.group(1)), int(m.group(2))
                size = max(w, h)
            elif "apple-touch" in path.name:
                size = 180
            elif "android-icon" in path.name:
                size = 192
            else:
                try:
                    with Image.open(path) as current:
                        size = max(current.size)
                except Exception:
                    size = 96
            img = icon(size)
            if img.size != (size, size):
                img = img.resize((size, size))
            img.save(path, format="PNG", optimize=True)

        ico = base / "favicon.ico"
        if ico.exists():
            icon(256).save(ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

    # Strip legacy metadata and cover the old product header in documentation screenshots.
    for path in (ROOT / "docs").rglob("*.png"):
        try:
            with Image.open(path) as current:
                im = current.convert("RGB")
        except Exception:
            continue
        w, h = im.size
        if w >= 400 and h >= 200:
            d = ImageDraw.Draw(im)
            bar_h = max(44, min(70, h // 10))
            d.rectangle((0, 0, w, bar_h), fill=(11, 11, 15))
            accent_x = max(18, bar_h // 3)
            cy = bar_h // 2
            d.ellipse((accent_x-7, cy-7, accent_x+7, cy+7), fill=(255, 122, 89))
            d.text((accent_x + 18, max(7, cy - 13)), "FinCo-Pilot", fill=(247, 247, 250), font=font(max(16, bar_h // 3), bold=True))
            im.save(path, format="PNG", optimize=True)
        else:
            im.save(path, format="PNG", optimize=True)


def repair_security_wording() -> None:
    # Sweep can turn a historical email sentence into awkward prose; curated SECURITY.md handles it.
    # Keep contributor docs functional and self-contained.
    contributing = ROOT / "CONTRIBUTING.md"
    if contributing.exists():
        text = contributing.read_text(encoding="utf-8")
        text = text.replace("Book 15 minutes", "Open a discussion issue")
        text = text.replace("Talk to the maintainer", "Contact the maintainer")
        contributing.write_text(text, encoding="utf-8")


def scan_for_legacy() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or path in SKIP_EXACT:
            continue
        rel = str(path.relative_to(ROOT))
        if any(p.search(rel) for p in LEGACY_PATTERNS):
            findings.append(f"PATH: {rel}")
        if not path.is_file() or not is_text_file(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in LEGACY_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"TEXT: {rel}:{line}: {match.group(0)}")
                break
    return sorted(set(findings))


def main() -> None:
    print("FinCo-Pilot identity migration: starting")
    changed = replace_text_everywhere()
    print(f"Text files transformed: {changed}")
    renamed = rename_legacy_paths()
    for src, dst in renamed:
        print(f"Renamed: {src} -> {dst}")

    # Run a second sweep after path moves, then apply curated brand surfaces.
    changed2 = replace_text_everywhere()
    print(f"Second-pass text files transformed: {changed2}")
    write_curated_files()
    update_brand_palette()
    update_ci_badge_publishing()
    repair_security_wording()
    regenerate_brand_images()

    findings = scan_for_legacy()
    if findings:
        print("\nLegacy identity scan FAILED:\n")
        for item in findings:
            print(item)
        raise SystemExit(2)

    print("Legacy identity scan passed: no tracked current-tree legacy brand tokens detected.")


if __name__ == "__main__":
    main()
