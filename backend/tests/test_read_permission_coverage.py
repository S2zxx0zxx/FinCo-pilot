"""Every read route must declare authentication or a reviewed public credential.

This supplements object-level A/B tests; an authentication dependency alone
never proves ownership or sufficient serialization scope.
"""
from app.main import app
from tests.test_write_permission_coverage import _api_routes, _dependency_names

# These routes are deliberately public or carry a narrower independent credential.
# New endpoints must add a real decision, not a blanket prefix exemption.
PUBLIC_READ_POLICIES = {
    '/api/auth/oidc/config': 'public identity-provider capability metadata',
    '/api/auth/oidc/login': 'starts authentication; state and redirect checks inside provider flow',
    '/api/auth/oidc/callback': 'completes authentication using state/code checks; not an app-session read',
    '/api/auth/clerk/config': 'public Clerk client configuration; no secret key',
    '/api/billing/catalog': 'public price catalog; cannot grant an entitlement',
    '/api/billing/founder-campaign': 'public offer availability; cannot grant an entitlement',
    '/api/connections/providers': 'public provider capability/configured booleans, no credentials',
    '/api/setup/status': 'bootstrap-needed boolean only; admin creation has separate atomic guard',
    '/api/currencies': 'public currency reference data',
    '/api/fiscal/jurisdictions': 'public fiscal jurisdiction reference data',
    '/api/settings/attachments': 'public allowed types and size/count limits; no storage credentials',
    '/api/admin/registration-status': 'public signup availability, not admin authority',
    '/api/admin/default-colors': 'public theme defaults, not admin authority',
    '/api/public/invoices/{token}': 'scoped high-entropy revocable document-share credential',
    '/api/public/invoices/{token}/logo': 'same scoped document-share credential',
    '/api/public/invoices/{token}/pdf': 'same scoped document-share credential',
    '/api/account-deletion/{identity}/status': 'independent X-Deletion-Receipt header checked in handler',
    '/api/workspace-deletion/{identity}/status': 'independent X-Deletion-Receipt header checked in handler',
    '/api/support/info': 'public support availability/contact configuration',
    '/api/privacy-policy': 'public approved policy publication contract',
    '/api/terms': 'public approved terms publication contract',
    '/api/info': 'public application/operator metadata only',
    '/api/agents/info': 'public agents capability metadata only',
    '/api/health/live': 'public process liveness without financial data',
    '/api/health': 'public process liveness without financial data',
    '/api/health/ready': 'public minimized readiness booleans/errors without credentials',
    '/metrics': 'disabled unless configured; constant-time independent monitoring bearer check',
}


def test_every_read_has_authentication_or_reviewed_public_policy():
    reads = [route for route in _api_routes(app.routes) if 'GET' in route.methods]
    assert len(reads) > 100, 'Route traversal must not silently stop checking reads'
    uncovered = []
    for route in reads:
        if route.path in PUBLIC_READ_POLICIES:
            continue
        names = _dependency_names(route)
        if not names.intersection({'current_user_dependency', 'current_superuser',
                                   'current_workspace', 'current_writable_workspace'}):
            uncovered.append(route.path)
    assert not uncovered, f'Reads lack a declared authentication/policy decision: {uncovered}'


def test_public_read_exceptions_are_current_routes():
    paths = {route.path for route in _api_routes(app.routes) if 'GET' in route.methods}
    assert not (set(PUBLIC_READ_POLICIES) - paths), 'Remove stale public exceptions'
