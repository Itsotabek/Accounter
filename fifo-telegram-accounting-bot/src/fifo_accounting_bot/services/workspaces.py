from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fifo_accounting_bot.database import SessionFactory
from fifo_accounting_bot.models import (
    ApplicationUser,
    AuditEvent,
    ExternalIdentity,
    OperationReceipt,
    Organization,
    OrganizationMembership,
    SchemaRevision,
    TelegramUser,
)

PHASE_ZERO_REVISION = "phase0-organizations-v1"


@dataclass(frozen=True, slots=True)
class WorkspaceContext:
    """Resolved product identity and active books for one Telegram user."""

    telegram_user_id: int
    application_user_id: str
    organization_id: str
    organization_name: str
    accounting_scope_id: int
    organization_role: str
    is_platform_admin: bool
    base_currency: str | None
    country_code: str | None
    timezone_name: str


@dataclass(frozen=True, slots=True)
class BootstrapSummary:
    telegram_users: int
    application_users: int
    organizations: int
    revision_applied: bool


@dataclass(frozen=True, slots=True)
class OperationState:
    receipt_id: str
    status: str
    result_reference: str
    created: bool


class WorkspaceService:
    """Channel-neutral identity, organization, role, and audit boundary.

    Telegram is currently the only login provider. The future web application can
    link another ExternalIdentity to the same ApplicationUser and Organization,
    while the accounting services continue using ``accounting_scope_id`` during
    the compatibility period.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        platform_admin_telegram_ids: frozenset[int] = frozenset(),
    ) -> None:
        self._sessions = session_factory
        self._platform_admin_ids = platform_admin_telegram_ids

    def bootstrap_existing_telegram_users(self) -> BootstrapSummary:
        """Idempotently create product identities/workspaces for existing users."""

        with self._sessions.begin() as session:
            rows = list(
                session.scalars(
                    select(TelegramUser).order_by(TelegramUser.telegram_user_id)
                )
            )
            revision_applied = session.get(SchemaRevision, PHASE_ZERO_REVISION) is None
            for row in rows:
                self.ensure_for_telegram_in_session(session, row)
            if revision_applied:
                session.add(
                    SchemaRevision(
                        revision=PHASE_ZERO_REVISION,
                        details={"migrated_telegram_users": len(rows)},
                    )
                )
            application_users = session.scalar(
                select(func.count()).select_from(ApplicationUser)
            ) or 0
            organizations = session.scalar(
                select(func.count()).select_from(Organization)
            ) or 0
            return BootstrapSummary(
                telegram_users=len(rows),
                application_users=int(application_users),
                organizations=int(organizations),
                revision_applied=revision_applied,
            )

    def ensure_for_telegram_in_session(
        self, session: Session, telegram_user: TelegramUser
    ) -> WorkspaceContext:
        """Resolve or create the product identity inside an existing transaction."""

        now = datetime.now(timezone.utc)
        subject = str(telegram_user.telegram_user_id)
        identity = session.scalar(
            select(ExternalIdentity).where(
                ExternalIdentity.provider == "telegram",
                ExternalIdentity.subject == subject,
            )
        )
        created_identity = identity is None
        if identity is None:
            app_user = ApplicationUser(
                display_name=telegram_user.display_name,
                preferred_language=telegram_user.language,
                is_platform_admin=(
                    telegram_user.telegram_user_id in self._platform_admin_ids
                ),
            )
            session.add(app_user)
            session.flush()
            identity = ExternalIdentity(
                application_user_id=app_user.id,
                provider="telegram",
                subject=subject,
            )
            session.add(identity)
        else:
            app_user = session.get(ApplicationUser, identity.application_user_id)
            if app_user is None:  # Defensive guard for manually damaged databases.
                raise RuntimeError("External identity refers to a missing application user.")
            app_user.display_name = telegram_user.display_name
            app_user.preferred_language = telegram_user.language
            app_user.is_platform_admin = (
                telegram_user.telegram_user_id in self._platform_admin_ids
            )
            app_user.updated_at = now
            identity.last_seen_at = now

        organization = None
        if identity.active_organization_id:
            organization = session.get(Organization, identity.active_organization_id)
        if organization is None:
            organization = session.scalar(
                select(Organization).where(
                    Organization.accounting_scope_id
                    == telegram_user.telegram_user_id
                )
            )
        created_organization = organization is None
        if organization is None:
            organization = Organization(
                accounting_scope_id=telegram_user.telegram_user_id,
                name=self._default_business_name(telegram_user),
                default_language=telegram_user.language or "en",
            )
            session.add(organization)
            session.flush()
        elif organization.is_personal_default:
            organization.name = self._default_business_name(telegram_user)
            organization.default_language = telegram_user.language or "en"
            organization.updated_at = now

        membership = session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization.id,
                OrganizationMembership.application_user_id == app_user.id,
            )
        )
        if membership is None:
            membership = OrganizationMembership(
                organization_id=organization.id,
                application_user_id=app_user.id,
                role="owner",
                status="active",
            )
            session.add(membership)
        identity.active_organization_id = organization.id
        session.flush()

        if created_organization:
            session.add(
                AuditEvent(
                    organization_id=organization.id,
                    actor_user_id=app_user.id,
                    source="system",
                    action="organization.provisioned",
                    entity_type="organization",
                    entity_id=organization.id,
                    details={"compatibility_scope_created": True},
                )
            )
        if created_identity:
            session.add(
                AuditEvent(
                    organization_id=organization.id,
                    actor_user_id=app_user.id,
                    source="system",
                    action="identity.linked",
                    entity_type="external_identity",
                    entity_id=identity.id,
                    details={"provider": "telegram"},
                )
            )

        return self._context(telegram_user.telegram_user_id, app_user, organization, membership)

    def get_for_telegram(self, telegram_user_id: int) -> WorkspaceContext | None:
        with self._sessions() as session:
            identity = session.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.provider == "telegram",
                    ExternalIdentity.subject == str(telegram_user_id),
                )
            )
            if identity is None or identity.active_organization_id is None:
                return None
            app_user = session.get(ApplicationUser, identity.application_user_id)
            organization = session.get(Organization, identity.active_organization_id)
            if app_user is None or organization is None:
                return None
            membership = session.scalar(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization.id,
                    OrganizationMembership.application_user_id == app_user.id,
                    OrganizationMembership.status == "active",
                )
            )
            if membership is None:
                return None
            return self._context(telegram_user_id, app_user, organization, membership)

    def count_organizations(self) -> int:
        with self._sessions() as session:
            return int(
                session.scalar(select(func.count()).select_from(Organization)) or 0
            )

    def record_event(
        self,
        context: WorkspaceContext,
        action: str,
        *,
        source: str,
        entity_type: str = "",
        entity_id: str = "",
        details: dict[str, object] | None = None,
    ) -> str:
        """Append a non-message audit event and return its public ID."""

        with self._sessions.begin() as session:
            event = AuditEvent(
                organization_id=context.organization_id,
                actor_user_id=context.application_user_id,
                source=source,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details or {},
            )
            session.add(event)
            session.flush()
            return event.id

    def reserve_operation(
        self,
        context: WorkspaceContext,
        *,
        source: str,
        idempotency_key: str,
        operation: str,
    ) -> OperationState:
        """Reserve a cross-channel write key or return the existing receipt."""

        normalized_key = idempotency_key.strip()
        if not normalized_key or len(normalized_key) > 160:
            raise ValueError("idempotency_key must contain 1 to 160 characters")
        with self._sessions.begin() as session:
            receipt = session.scalar(
                select(OperationReceipt).where(
                    OperationReceipt.organization_id == context.organization_id,
                    OperationReceipt.source == source,
                    OperationReceipt.idempotency_key == normalized_key,
                )
            )
            if receipt is not None:
                return OperationState(
                    receipt_id=receipt.id,
                    status=receipt.status,
                    result_reference=receipt.result_reference,
                    created=False,
                )
            receipt = OperationReceipt(
                organization_id=context.organization_id,
                source=source,
                idempotency_key=normalized_key,
                operation=operation,
            )
            session.add(receipt)
            session.flush()
            return OperationState(
                receipt_id=receipt.id,
                status=receipt.status,
                result_reference=receipt.result_reference,
                created=True,
            )

    def finish_operation(
        self, receipt_id: str, *, status: str, result_reference: str = ""
    ) -> None:
        if status not in {"completed", "failed"}:
            raise ValueError("status must be completed or failed")
        with self._sessions.begin() as session:
            receipt = session.get(OperationReceipt, receipt_id)
            if receipt is None:
                raise LookupError("operation receipt not found")
            receipt.status = status
            receipt.result_reference = result_reference[:160]
            receipt.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _default_business_name(telegram_user: TelegramUser) -> str:
        label = telegram_user.display_name.strip()
        if not label and telegram_user.username:
            label = f"@{telegram_user.username}"
        return f"{label or 'My'} · Business"

    @staticmethod
    def _context(
        telegram_user_id: int,
        app_user: ApplicationUser,
        organization: Organization,
        membership: OrganizationMembership,
    ) -> WorkspaceContext:
        return WorkspaceContext(
            telegram_user_id=telegram_user_id,
            application_user_id=app_user.id,
            organization_id=organization.id,
            organization_name=organization.name,
            accounting_scope_id=organization.accounting_scope_id,
            organization_role=membership.role,
            is_platform_admin=app_user.is_platform_admin,
            base_currency=organization.base_currency,
            country_code=organization.country_code,
            timezone_name=organization.timezone_name,
        )
