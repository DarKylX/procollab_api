from typing import Any

from rest_framework.exceptions import ValidationError


REGISTRATION_CONSENT_KEYS = (
    "personal_data_consent",
    "personalDataConsent",
    "legal_consent",
    "legalConsent",
    "participant_consent",
    "participantConsent",
)

REGISTRATION_REQUIRED_DOCUMENT_TYPES = (
    "privacy_policy",
    "participant_consent",
    "participation_terms",
)


def active_legal_documents_by_type() -> dict[str, Any]:
    from partner_programs.models import LegalDocument

    docs = LegalDocument.objects.filter(is_active=True).order_by(
        "type", "-created_at", "-id"
    )
    result = {}
    for doc in docs:
        result.setdefault(doc.type, doc)
    return result


def document_snapshot(document) -> str:
    if not document:
        return ""
    if document.content_html:
        return document.content_html
    return document.content_url or ""


def request_has_registration_consent(data: dict[str, Any]) -> bool:
    return any(
        data.get(key) is True or data.get(key) == "true"
        for key in REGISTRATION_CONSENT_KEYS
    )


def strip_registration_consent_keys(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if key not in REGISTRATION_CONSENT_KEYS}


def create_participant_consent(*, program, user, request) -> None:
    from partner_programs.models import PartnerProgramParticipantConsent

    active_docs = active_legal_documents_by_type()
    missing = [
        doc_type
        for doc_type in REGISTRATION_REQUIRED_DOCUMENT_TYPES
        if doc_type not in active_docs
    ]
    if missing:
        raise ValidationError(
            {
                "detail": "Registration is temporarily unavailable: required legal documents are not active.",
                "missing_legal_documents": missing,
            }
        )

    if not request_has_registration_consent(request.data):
        raise ValidationError(
            {
                "personal_data_consent": "Explicit personal data processing consent is required."
            }
        )

    privacy_doc = active_docs["privacy_policy"]
    consent_doc = active_docs["participant_consent"]
    terms_doc = active_docs["participation_terms"]

    PartnerProgramParticipantConsent.objects.create(
        program=program,
        user=user if getattr(user, "is_authenticated", False) else None,
        consent_document_version=consent_doc.version,
        privacy_policy_version=privacy_doc.version,
        participation_terms_version=terms_doc.version,
        consent_text_snapshot="\n\n".join(
            part
            for part in (
                document_snapshot(consent_doc),
                document_snapshot(privacy_doc),
                document_snapshot(terms_doc),
            )
            if part
        ),
        ip_address=_request_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
    )


def _request_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    return request.META.get("REMOTE_ADDR", "") or None
