from __future__ import annotations

from sqlalchemy import func, select

from fifo_accounting_bot.models import (
    ApplicationUser,
    AuditEvent,
    ExternalIdentity,
    OperationReceipt,
    Organization,
    OrganizationMembership,
    Product,
    SchemaRevision,
    TelegramUser,
)
from fifo_accounting_bot.services.users import UserService
from fifo_accounting_bot.services.workspaces import PHASE_ZERO_REVISION, WorkspaceService


def test_touch_provisions_channel_neutral_identity_and_business(inventory):
    _, session_factory = inventory
    users = UserService(session_factory, frozenset({99}))

    profile = users.touch(99, "owner", "Example Owner")
    workspace = users.get_workspace(99)

    assert profile.telegram_user_id == 99
    assert workspace is not None
    assert workspace.accounting_scope_id == 99
    assert workspace.organization_name == "Example Owner · Business"
    assert workspace.organization_role == "owner"
    assert workspace.is_platform_admin is True

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ApplicationUser)) == 1
        assert session.scalar(select(func.count()).select_from(ExternalIdentity)) == 1
        assert session.scalar(select(func.count()).select_from(Organization)) == 1
        assert session.scalar(select(func.count()).select_from(OrganizationMembership)) == 1
        assert session.scalar(select(func.count()).select_from(AuditEvent)) == 2


def test_workspace_bootstrap_is_idempotent_and_records_revision(inventory):
    _, session_factory = inventory
    users = UserService(session_factory)
    users.touch(10, "one", "One")
    users.touch(20, "two", "Two")

    first = users.bootstrap_workspaces()
    second = users.bootstrap_workspaces()

    assert first.telegram_users == 2
    assert first.organizations == 2
    assert first.revision_applied is True
    assert second.organizations == 2
    assert second.revision_applied is False
    with session_factory() as session:
        assert session.get(SchemaRevision, PHASE_ZERO_REVISION) is not None
        assert session.scalar(select(func.count()).select_from(AuditEvent)) == 4


def test_operation_receipts_prevent_cross_channel_duplicate_writes(inventory):
    _, session_factory = inventory
    users = UserService(session_factory)
    users.touch(99, "tester", "Test User")
    workspace = users.get_workspace(99)
    assert workspace is not None
    workspace_service = WorkspaceService(session_factory)

    created = workspace_service.reserve_operation(
        workspace,
        source="telegram",
        idempotency_key="update-100:confirm-sale",
        operation="inventory.sale",
    )
    repeated = workspace_service.reserve_operation(
        workspace,
        source="telegram",
        idempotency_key="update-100:confirm-sale",
        operation="inventory.sale",
    )
    workspace_service.finish_operation(
        created.receipt_id, status="completed", result_reference="sale:42"
    )

    assert created.created is True
    assert repeated.created is False
    assert repeated.receipt_id == created.receipt_id
    with session_factory() as session:
        receipt = session.get(OperationReceipt, created.receipt_id)
        assert receipt is not None
        assert receipt.status == "completed"
        assert receipt.result_reference == "sale:42"


def test_language_preference_is_shared_with_future_clients(inventory):
    _, session_factory = inventory
    users = UserService(session_factory)
    users.touch(99, "tester", "Test User")

    users.set_language(99, "it")

    with session_factory() as session:
        identity = session.scalar(
            select(ExternalIdentity).where(
                ExternalIdentity.provider == "telegram",
                ExternalIdentity.subject == "99",
            )
        )
        assert identity is not None
        app_user = session.get(ApplicationUser, identity.application_user_id)
        organization = session.get(Organization, identity.active_organization_id)
        assert app_user is not None and app_user.preferred_language == "it"
        assert organization is not None and organization.default_language == "it"


def test_bootstrap_preserves_existing_accounting_scope_and_records(inventory):
    _, session_factory = inventory
    with session_factory.begin() as session:
        session.add(
            TelegramUser(
                telegram_user_id=77,
                username="legacy",
                display_name="Legacy Owner",
                language="en",
            )
        )
        session.add(Product(owner_id=77, sku="KEEP-1", name="Keep me", unit="pcs"))

    users = UserService(session_factory)
    users.bootstrap_workspaces()

    workspace = users.get_workspace(77)
    assert workspace is not None and workspace.accounting_scope_id == 77
    with session_factory() as session:
        product = session.scalar(select(Product).where(Product.sku == "KEEP-1"))
        assert product is not None
        assert product.owner_id == 77
        assert product.name == "Keep me"
