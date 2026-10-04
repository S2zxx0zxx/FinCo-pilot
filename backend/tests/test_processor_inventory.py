from app.core.processor_inventory import (
    INVENTORY_ID,
    THIRD_PARTY_BOUNDARIES,
    BoundaryStatus,
    DeletionExpectation,
    LegalRoleStatus,
    get_third_party_boundary,
    unresolved_operator_boundaries,
)


def test_inventory_is_self_keyed_and_documents_every_boundary():
    assert len(THIRD_PARTY_BOUNDARIES) >= 14
    for key, boundary in THIRD_PARTY_BOUNDARIES.items():
        assert boundary.key == key
        assert boundary.service.strip()
        assert boundary.purpose.strip()
        assert boundary.data_classes
        assert boundary.roadmap_gates
        assert boundary.notes.strip()


def test_selected_processors_are_release_gated_not_silently_approved():
    assert get_third_party_boundary("zoho_desk").status is BoundaryStatus.SELECTED_RELEASE_GATED
    assert get_third_party_boundary("razorpay").status is BoundaryStatus.SELECTED_RELEASE_GATED
    assert (
        get_third_party_boundary("managed_postgresql").status
        is BoundaryStatus.SELECTED_RELEASE_GATED
    )
    assert (
        get_third_party_boundary("cloudflare_edge").status
        is BoundaryStatus.SELECTED_RELEASE_GATED
    )

    unresolved = {item.key for item in unresolved_operator_boundaries()}
    assert "zoho_desk" in unresolved
    assert "razorpay" in unresolved
    assert "managed_postgresql" in unresolved
    assert "cloudflare_edge" in unresolved


def test_core_ai_upstream_is_unresolved_and_high_sensitivity():
    boundary = get_third_party_boundary("operator_ai_upstream")
    assert boundary.status is BoundaryStatus.UNRESOLVED
    assert boundary.sends_personal_data is True
    assert boundary.sends_financial_data is True
    assert 6 in boundary.roadmap_gates
    assert 49 in boundary.roadmap_gates
    assert 50 in boundary.roadmap_gates


def test_omniroute_is_internal_not_the_external_model_processor():
    boundary = get_third_party_boundary("omniroute")
    assert boundary.status is BoundaryStatus.INTERNAL_SELF_HOSTED
    assert boundary.is_external is False
    assert boundary.legal_role is LegalRoleStatus.NOT_APPLICABLE_INTERNAL


def test_bank_connectors_require_revoke_then_delete():
    for key in ("pluggy", "enable_banking", "simplefin"):
        boundary = get_third_party_boundary(key)
        assert boundary.status is BoundaryStatus.OPTIONAL_RELEASE_GATED
        assert boundary.sends_personal_data is True
        assert boundary.sends_financial_data is True
        assert boundary.deletion is DeletionExpectation.REVOKE_THEN_DELETE


def test_user_directed_recipients_are_not_core_operator_routes():
    for key in ("user_configured_llm", "external_mcp_servers"):
        boundary = get_third_party_boundary(key)
        assert boundary.status is BoundaryStatus.USER_DIRECTED
        assert boundary.deletion is DeletionExpectation.USER_DIRECTED_PROVIDER


def test_unselected_infrastructure_remains_unresolved():
    for key in (
        "smtp_provider",
        "hosting_logging_provider",
        "managed_redis",
        "oidc_provider",
    ):
        boundary = get_third_party_boundary(key)
        assert boundary.status is BoundaryStatus.UNRESOLVED
        assert boundary.legal_role is LegalRoleStatus.CONTRACT_REVIEW_REQUIRED


def test_selected_cloudflare_edge_is_separate_from_compute_host():
    edge = get_third_party_boundary("cloudflare_edge")
    assert edge.service == "Cloudflare DNS / TLS edge / Tunnel"
    assert edge.status is BoundaryStatus.SELECTED_RELEASE_GATED
    assert edge.sends_personal_data is True
    assert edge.sends_financial_data is True
    assert edge.sends_secrets_or_credentials is True
    assert edge.deletion is DeletionExpectation.CONTRACTUAL_RETENTION_THEN_DELETE

    compute = get_third_party_boundary("hosting_logging_provider")
    assert compute.status is BoundaryStatus.UNRESOLVED
    assert "compute" in compute.service.lower()


def test_selected_object_storage_boundary_stays_release_gated():
    boundary = get_third_party_boundary("object_storage_provider")
    assert boundary.service == "Cloudflare R2"
    assert boundary.status is BoundaryStatus.SELECTED_RELEASE_GATED
    assert boundary.sends_personal_data is True
    assert boundary.sends_financial_data is True
    assert boundary.deletion is DeletionExpectation.OPERATOR_INFRA_LIFECYCLE
    assert 16 in boundary.roadmap_gates
    assert 25 in boundary.roadmap_gates


def test_selected_postgresql_boundary_stays_release_gated():
    boundary = get_third_party_boundary("managed_postgresql")
    assert boundary.service == "Neon Postgres"
    assert boundary.status is BoundaryStatus.SELECTED_RELEASE_GATED
    assert boundary.sends_personal_data is True
    assert boundary.sends_financial_data is True
    assert 14 in boundary.roadmap_gates
    assert 25 in boundary.roadmap_gates


def test_open_exchange_rates_receives_no_product_personal_data_by_design():
    boundary = get_third_party_boundary("open_exchange_rates")
    assert boundary.status is BoundaryStatus.NO_PERSONAL_DATA_BY_DESIGN
    assert boundary.sends_personal_data is False
    assert boundary.sends_financial_data is False
    assert (
        boundary.legal_role
        is LegalRoleStatus.NOT_A_PERSONAL_DATA_RECIPIENT_BY_DESIGN
    )


def test_unknown_boundary_fails_closed():
    try:
        get_third_party_boundary("future_unreviewed_vendor")
    except KeyError as exc:
        assert "Unknown third-party boundary" in str(exc)
    else:
        raise AssertionError("Unknown external recipients must not inherit approval")


def test_inventory_contract_id_and_reference_boundaries_are_explicit():
    assert INVENTORY_ID == "FINCO_THIRD_PARTY_PROCESSOR_INVENTORY_V1"

    for key in ("open_exchange_rates", "yahoo_finance", "tesouro_direto"):
        boundary = get_third_party_boundary(key)
        assert boundary.status is BoundaryStatus.NO_PERSONAL_DATA_BY_DESIGN
        assert boundary.sends_personal_data is False

    security = get_third_party_boundary("github_private_vulnerability_reporting")
    assert security.status is BoundaryStatus.USER_DIRECTED
    assert security.sends_financial_data is False
