from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import conditional_escape
from PIL import Image, UnidentifiedImageError
from weasyprint import HTML

from certificates.enums import (
    CERTIFICATE_FIELD_KEYS,
    CERTIFICATE_TYPE_PARTICIPATION,
    FIELD_CERTIFICATE_ID,
    FIELD_COMPLETION_DATE,
    FIELD_ORGANIZER_NAME,
    FIELD_PARTICIPANT_FULL_NAME,
    FIELD_PROGRAM_TITLE,
    FIELD_PROJECT_TITLE,
    FIELD_RANK,
    FIELD_SIGNER_NAME,
    FIELD_TEAM_MEMBERS,
    FONT_CSS_FAMILIES,
    ISSUE_CONDITION_SUBMITTED_PROJECT,
    LEGACY_FIELD_KEY_MAP,
    RELEASE_MODE_AFTER_PROGRAM_END,
    RELEASE_MODE_MANUAL,
    get_default_fields_positioning,
)
from certificates.models import (
    CertificateGenerationRun,
    IssuedCertificate,
    ProgramCertificateTemplate,
)
from files.models import UserFile
from files.service import CDN, get_default_storage
from partner_programs.models import (
    PartnerProgram,
    PartnerProgramProject,
    PartnerProgramUserProfile,
)
from project_rates.models import ProjectScore

ALLOWED_BACKGROUND_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
ALLOWED_BACKGROUND_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/pdf",
}
ALLOWED_ASSET_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_ASSET_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_BACKGROUND_IMAGE_SIZE = 10 * 1024 * 1024
MAX_CERTIFICATE_ASSET_SIZE = 10 * 1024 * 1024
MIN_BACKGROUND_WIDTH = 800
MIN_BACKGROUND_HEIGHT = 600
ALIGNMENTS = {"left", "center", "right"}
DEFAULT_SIGNER_NAME = "Анна Смирнова"
DEFAULT_SIGNATURE_POSITION = {"x": 0.60, "y": 0.79, "width": 0.16}
DEFAULT_STAMP_POSITION = {"x": 0.43, "y": 0.80, "width": 0.13}
DEFAULT_COMPANY_LOGO_POSITION = {"x": 0.78, "y": 0.13, "width": 0.18}

PREVIEW_TEST_DATA = {
    FIELD_PARTICIPANT_FULL_NAME: "Иван Петров",
    FIELD_PROGRAM_TITLE: "Финансовый форсайт 2026",
    FIELD_COMPLETION_DATE: "15 июля 2026",
    FIELD_ORGANIZER_NAME: "PROCOLLAB",
    FIELD_CERTIFICATE_ID: "CERT-2026-000124",
    FIELD_PROJECT_TITLE: "AI-модель оценки рисков",
    FIELD_TEAM_MEMBERS: "Иван Петров, Анна Смирнова",
    FIELD_RANK: "",
    FIELD_SIGNER_NAME: DEFAULT_SIGNER_NAME,
}


class CertificateTemplateConflictError(Exception):
    pass


@dataclass(frozen=True)
class CertificateRecipient:
    user_id: int
    program_project_id: int | None = None
    project_id: int | None = None
    final_score: Decimal | None = None
    rating_position: int | None = None


def validate_background_file_metadata(user_file: UserFile) -> None:
    extension = (user_file.extension or "").lower().lstrip(".")
    mime_type = (user_file.mime_type or "").lower()

    if extension not in ALLOWED_BACKGROUND_EXTENSIONS:
        raise DjangoValidationError("Background file must be PDF, PNG or JPG.")
    if mime_type and mime_type not in ALLOWED_BACKGROUND_MIME_TYPES:
        raise DjangoValidationError("Background file must be PDF, PNG or JPG.")
    if user_file.size and user_file.size > MAX_BACKGROUND_IMAGE_SIZE:
        raise DjangoValidationError("Background file size must not exceed 10 MB.")

    if extension == "pdf" or mime_type == "application/pdf":
        return

    dimensions = get_user_file_image_dimensions(user_file)
    if dimensions is None:
        return

    validate_image_dimensions(*dimensions)


def validate_uploaded_background_file(uploaded_file) -> None:
    extension = Path(uploaded_file.name or "").suffix.lower().lstrip(".")
    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()

    if extension not in ALLOWED_BACKGROUND_EXTENSIONS:
        raise DjangoValidationError("Background upload must be PDF, PNG or JPG.")
    if content_type and content_type not in ALLOWED_BACKGROUND_MIME_TYPES:
        raise DjangoValidationError("Background upload must be PDF, PNG or JPG.")
    if uploaded_file.size and uploaded_file.size > MAX_BACKGROUND_IMAGE_SIZE:
        raise DjangoValidationError("Background file size must not exceed 10 MB.")

    if extension == "pdf" or content_type == "application/pdf":
        uploaded_file.seek(0)
        return

    try:
        image = Image.open(uploaded_file)
        width, height = image.size
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise DjangoValidationError("Background image is not a valid image.")
    finally:
        uploaded_file.seek(0)

    validate_image_dimensions(width, height)


def validate_certificate_asset_file_metadata(user_file: UserFile) -> None:
    extension = (user_file.extension or "").lower().lstrip(".")
    mime_type = (user_file.mime_type or "").lower()

    if extension not in ALLOWED_ASSET_EXTENSIONS:
        raise DjangoValidationError("Certificate asset must be PNG or JPG.")
    if mime_type and mime_type not in ALLOWED_ASSET_MIME_TYPES:
        raise DjangoValidationError("Certificate asset must be PNG or JPG.")
    if user_file.size and user_file.size > MAX_CERTIFICATE_ASSET_SIZE:
        raise DjangoValidationError("Certificate asset size must not exceed 10 MB.")

    get_user_file_image_dimensions(user_file)


def validate_uploaded_certificate_asset_file(uploaded_file) -> None:
    extension = Path(uploaded_file.name or "").suffix.lower().lstrip(".")
    content_type = (getattr(uploaded_file, "content_type", "") or "").lower()

    if extension not in ALLOWED_ASSET_EXTENSIONS:
        raise DjangoValidationError("Certificate asset upload must be PNG or JPG.")
    if content_type and content_type not in ALLOWED_ASSET_MIME_TYPES:
        raise DjangoValidationError("Certificate asset upload must be PNG or JPG.")
    if uploaded_file.size and uploaded_file.size > MAX_CERTIFICATE_ASSET_SIZE:
        raise DjangoValidationError("Certificate asset size must not exceed 10 MB.")

    try:
        image = Image.open(uploaded_file)
        image.verify()
    except (UnidentifiedImageError, OSError):
        raise DjangoValidationError("Certificate asset is not a valid image.")
    finally:
        uploaded_file.seek(0)


def validate_image_dimensions(width: int, height: int) -> None:
    if width < MIN_BACKGROUND_WIDTH or height < MIN_BACKGROUND_HEIGHT:
        raise DjangoValidationError(
            "Background image dimensions must be at least 800x600."
        )


def get_user_file_image_dimensions(user_file: UserFile) -> tuple[int, int] | None:
    local_path = get_local_media_path(user_file.link)
    if local_path and local_path.exists():
        try:
            with Image.open(local_path) as image:
                return image.size
        except (UnidentifiedImageError, OSError):
            raise DjangoValidationError("Background image is not a valid image.")

    parsed = urlparse(user_file.link)
    if parsed.scheme in {"http", "https"}:
        try:
            response = requests.get(user_file.link, timeout=5)
            response.raise_for_status()
            with Image.open(BytesIO(response.content)) as image:
                return image.size
        except (requests.RequestException, UnidentifiedImageError, OSError, ValueError):
            return None

    return None


def get_local_media_path(url: str) -> Path | None:
    parsed = urlparse(url)
    path = unquote(parsed.path if parsed.scheme else url)
    media_url = settings.MEDIA_URL.rstrip("/") + "/"
    if not path.startswith(media_url):
        return None

    relative_path = path.removeprefix(media_url)
    file_path = (Path(settings.MEDIA_ROOT) / relative_path).resolve()
    media_root = Path(settings.MEDIA_ROOT).resolve()
    if file_path == media_root or media_root not in file_path.parents:
        return None
    return file_path


def validate_fields_positioning(value: dict) -> dict:
    if not isinstance(value, dict):
        raise DjangoValidationError("field_positions must be an object.")

    normalized = normalize_fields_positioning(value)
    for field_key, config in normalized.items():
        if field_key not in CERTIFICATE_FIELD_KEYS:
            continue
        if not isinstance(config, dict):
            raise DjangoValidationError(f"{field_key} positioning must be an object.")

        for coordinate in ("x", "y"):
            coordinate_value = config.get(coordinate)
            if not isinstance(coordinate_value, (int, float)):
                raise DjangoValidationError(f"{field_key}.{coordinate} must be numeric.")
            if not 0 <= coordinate_value <= 1:
                raise DjangoValidationError(
                    f"{field_key}.{coordinate} must be from 0 to 1."
                )

        font_size = config.get("font_size")
        if not isinstance(font_size, (int, float)) or font_size <= 0:
            raise DjangoValidationError(f"{field_key}.font_size must be positive.")

        if config.get("align") not in ALIGNMENTS:
            raise DjangoValidationError(f"{field_key}.align must be left, center or right.")

        if not isinstance(config.get("visible"), bool):
            raise DjangoValidationError(f"{field_key}.visible must be boolean.")

    return normalized


def normalize_asset_position(value: dict | None, defaults: dict) -> dict:
    normalized = dict(defaults)
    if not value:
        return normalized
    if not isinstance(value, dict):
        raise DjangoValidationError("asset position must be an object.")

    for key in ("x", "y", "width"):
        if key in value:
            normalized[key] = value[key]
    return normalized


def validate_asset_position(value: dict, defaults: dict) -> dict:
    normalized = normalize_asset_position(value, defaults)
    for key in ("x", "y", "width"):
        item = normalized.get(key)
        if not isinstance(item, (int, float)):
            raise DjangoValidationError(f"{key} must be numeric.")
        if key in ("x", "y") and not 0 <= item <= 1:
            raise DjangoValidationError(f"{key} must be from 0 to 1.")
        if key == "width" and not 0.03 <= item <= 0.5:
            raise DjangoValidationError("width must be from 0.03 to 0.5.")
    return normalized


def normalize_fields_positioning(value: dict | None) -> dict:
    merged = deepcopy(get_default_fields_positioning())
    if not value:
        return merged

    for raw_key, raw_config in value.items():
        key = LEGACY_FIELD_KEY_MAP.get(raw_key, raw_key)
        if key not in merged or not isinstance(raw_config, dict):
            continue

        config = dict(raw_config)
        if "visible" not in config and "enabled" in config:
            config["visible"] = config["enabled"]
        config.pop("enabled", None)
        merged[key].update(config)

    return merged


def merge_fields_positioning(value: dict | None) -> dict:
    return normalize_fields_positioning(value)


def upload_background_image(uploaded_file, user) -> UserFile:
    info = CDN(storage=get_default_storage()).upload(
        uploaded_file,
        user,
        preserve_original=True,
    )
    return UserFile.objects.create(
        user=user,
        link=info.url,
        name=info.name,
        extension=info.extension,
        mime_type=info.mime_type,
        size=info.size,
    )


def upload_certificate_asset_image(uploaded_file, user) -> UserFile:
    validate_uploaded_certificate_asset_file(uploaded_file)
    info = CDN(storage=get_default_storage()).upload(
        uploaded_file,
        user,
        preserve_original=True,
    )
    return UserFile.objects.create(
        user=user,
        link=info.url,
        name=info.name,
        extension=info.extension,
        mime_type=info.mime_type,
        size=info.size,
    )


def ensure_template_can_be_deleted(template) -> None:
    if program_has_issued_certificates(template.program_id):
        raise CertificateTemplateConflictError(
            "Certificate template cannot be deleted after certificates were issued."
        )


def program_has_issued_certificates(program_id: int) -> bool:
    return IssuedCertificate.objects.filter(program_id=program_id).exists()


def render_certificate_preview_html(template_data: dict) -> str:
    values = dict(PREVIEW_TEST_DATA)
    if template_data.get("signer_name"):
        values[FIELD_SIGNER_NAME] = template_data["signer_name"]
    return render_certificate_html_from_values(
        template_data=template_data,
        values=values,
    )


def render_certificate_preview_pdf(template_data: dict) -> bytes:
    return render_pdf_bytes(render_certificate_preview_html(template_data))


def get_certificate_recipients(
    program: PartnerProgram,
    template: ProgramCertificateTemplate | None = None,
) -> list[CertificateRecipient]:
    template = template or program.certificate_template
    if template.issue_condition_type != ISSUE_CONDITION_SUBMITTED_PROJECT:
        return []

    submitted_links = (
        PartnerProgramProject.objects.filter(
            partner_program=program,
            submitted=True,
        )
        .select_related("project", "project__leader")
        .prefetch_related("project__collaborator_set__user")
        .order_by("id")
    )
    link_by_project_id = {link.project_id: link for link in submitted_links}
    if not link_by_project_id:
        return []

    profiles = (
        PartnerProgramUserProfile.objects.filter(
            partner_program=program,
            user_id__isnull=False,
            project_id__in=link_by_project_id.keys(),
        )
        .select_related("user", "project")
        .order_by("id")
    )

    recipients: list[CertificateRecipient] = []
    seen_pairs: set[tuple[int, int]] = set()
    for profile in profiles:
        link = link_by_project_id.get(profile.project_id)
        if not link:
            continue

        pair = (profile.user_id, link.id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        recipients.append(
            CertificateRecipient(
                user_id=profile.user_id,
                program_project_id=link.id,
                project_id=link.project_id,
            )
        )

    return recipients


def calculate_project_final_score(
    program_id: int, project_id: int | None
) -> Decimal | None:
    if not project_id:
        return None

    raw_values = ProjectScore.objects.filter(
        project_id=project_id,
        criteria__partner_program_id=program_id,
        criteria__type__in=("int", "float"),
    ).values_list("value", flat=True)
    scores = []
    for raw_value in raw_values:
        try:
            scores.append(Decimal(str(raw_value)))
        except (InvalidOperation, TypeError):
            continue

    if not scores:
        return None

    average = sum(scores) / Decimal(len(scores))
    return average.quantize(Decimal("0.01"))


def generate_certificates_for_program_sync(
    program: PartnerProgram,
    *,
    regenerate: bool = True,
) -> CertificateGenerationRun:
    template = get_enabled_template_or_error(program)
    recipients = get_certificate_recipients(program, template)
    run = CertificateGenerationRun.objects.create(
        program=program,
        status=CertificateGenerationRun.STATUS_RUNNING,
        total_expected=len(recipients),
        enqueued_count=len(recipients),
    )

    issued_count = 0
    error_count = 0
    errors: list[str] = []
    for recipient in recipients:
        try:
            generate_certificate_for_recipient(
                program=program,
                template=template,
                recipient=recipient,
                regenerate=regenerate,
            )
            issued_count += 1
        except Exception as exc:
            error_count += 1
            errors.append(f"user_id={recipient.user_id}: {exc}")

    completed_at = timezone.now()
    run.issued_count = issued_count
    run.error_count = error_count
    run.status = (
        CertificateGenerationRun.STATUS_FAILED
        if error_count and not issued_count
        else CertificateGenerationRun.STATUS_COMPLETED
    )
    run.error_message = "\n".join(errors[:10])
    run.completed_at = completed_at
    run.save(
        update_fields=[
            "issued_count",
            "error_count",
            "status",
            "error_message",
            "completed_at",
            "datetime_updated",
        ]
    )

    template.generated_at = completed_at
    template.save(update_fields=["generated_at", "datetime_updated"])
    return run


def get_enabled_template_or_error(
    program: PartnerProgram,
) -> ProgramCertificateTemplate:
    try:
        template = program.certificate_template
    except ProgramCertificateTemplate.DoesNotExist:
        raise DjangoValidationError("Certificate settings were not configured.")

    if not template.is_enabled:
        raise DjangoValidationError("Certificates are disabled.")
    if template.issue_condition_type != ISSUE_CONDITION_SUBMITTED_PROJECT:
        raise DjangoValidationError("Only submitted_project is supported.")
    if template.certificate_type != CERTIFICATE_TYPE_PARTICIPATION:
        raise DjangoValidationError("Only participation certificates are supported.")
    return template


def generate_certificate_for_user(
    *,
    program_id: int,
    user_id: int,
    run_id: int | None = None,
    regenerate: bool = True,
) -> IssuedCertificate | None:
    program = PartnerProgram.objects.select_related("certificate_template").get(
        pk=program_id
    )
    template = get_enabled_template_or_error(program)
    recipient = get_recipient_for_user(program, template, user_id)
    if recipient is None:
        return None

    certificate = generate_certificate_for_recipient(
        program=program,
        template=template,
        recipient=recipient,
        regenerate=regenerate,
    )
    if run_id:
        CertificateGenerationRun.objects.filter(pk=run_id).update(
            issued_count=F("issued_count") + 1
        )
    return certificate


def get_recipient_for_user(
    program: PartnerProgram,
    template: ProgramCertificateTemplate,
    user_id: int,
) -> CertificateRecipient | None:
    for recipient in get_certificate_recipients(program, template):
        if recipient.user_id == user_id:
            return recipient
    return None


def generate_certificate_for_recipient(
    *,
    program: PartnerProgram,
    template: ProgramCertificateTemplate,
    recipient: CertificateRecipient,
    regenerate: bool,
) -> IssuedCertificate:
    existing = (
        IssuedCertificate.objects.filter(
            program=program,
            user_id=recipient.user_id,
            program_project_id=recipient.program_project_id,
        )
        .exclude(status=IssuedCertificate.STATUS_REVOKED)
        .select_related("pdf_file")
        .first()
    )

    if existing and not regenerate:
        return existing

    certificate_id = (
        existing.certificate_id
        if existing and existing.certificate_id
        else build_next_certificate_id(program.id, recipient.user_id)
    )
    certificate_uuid = existing.certificate_uuid if existing else None
    if certificate_uuid is None:
        certificate_uuid = IssuedCertificate._meta.get_field("certificate_uuid").default()

    html = render_certificate_html(
        program=program,
        template=template,
        recipient=recipient,
        certificate_id=certificate_id,
    )
    pdf_bytes = render_pdf_bytes(html)
    pdf_info = upload_certificate_pdf(
        pdf_bytes=pdf_bytes,
        program=program,
        user_id=recipient.user_id,
        certificate_id=certificate_id,
    )

    try:
        with transaction.atomic():
            pdf_file = UserFile.objects.create(
                user_id=recipient.user_id,
                link=pdf_info.url,
                name=pdf_info.name,
                extension=pdf_info.extension,
                mime_type=pdf_info.mime_type,
                size=pdf_info.size,
            )
            now = timezone.now()
            if existing:
                existing.program_project_id = recipient.program_project_id
                existing.pdf_file = pdf_file
                existing.status = IssuedCertificate.STATUS_GENERATED
                existing.generated_at = now
                existing.final_score = recipient.final_score
                existing.rating_position = recipient.rating_position
                existing.team_name = ""
                existing.save(
                    update_fields=[
                        "program_project",
                        "pdf_file",
                        "status",
                        "generated_at",
                        "final_score",
                        "rating_position",
                        "team_name",
                    ]
                )
                return existing

            return IssuedCertificate.objects.create(
                program=program,
                user_id=recipient.user_id,
                program_project_id=recipient.program_project_id,
                certificate_id=certificate_id,
                certificate_uuid=certificate_uuid,
                pdf_file=pdf_file,
                status=IssuedCertificate.STATUS_GENERATED,
                generated_at=now,
                final_score=recipient.final_score,
                rating_position=recipient.rating_position,
                team_name="",
            )
    except IntegrityError:
        CDN(storage=get_default_storage()).delete(pdf_info.url)
        certificate = (
            IssuedCertificate.objects.filter(
                program=program,
                user_id=recipient.user_id,
                program_project_id=recipient.program_project_id,
            )
            .exclude(status=IssuedCertificate.STATUS_REVOKED)
            .first()
        )
        if certificate is None:
            raise
        return certificate
    except Exception:
        CDN(storage=get_default_storage()).delete(pdf_info.url)
        raise


def build_next_certificate_id(program_id: int, user_id: int) -> str:
    sequence = IssuedCertificate.objects.filter(program_id=program_id).count() + 1
    while True:
        certificate_id = f"CERT-{program_id}-{user_id}-{sequence:06d}"
        if not IssuedCertificate.objects.filter(certificate_id=certificate_id).exists():
            return certificate_id
        sequence += 1


def render_certificate_html(
    *,
    program: PartnerProgram,
    template: ProgramCertificateTemplate,
    recipient: CertificateRecipient,
    certificate_id: str | None = None,
    certificate_uuid=None,
) -> str:
    User = get_user_model()
    user = User.objects.get(pk=recipient.user_id)
    project = None
    if recipient.program_project_id:
        program_project = (
            PartnerProgramProject.objects.select_related("project", "project__leader")
            .prefetch_related("project__collaborator_set__user")
            .get(pk=recipient.program_project_id)
        )
        project = program_project.project
    certificate_display_id = certificate_id or str(certificate_uuid or "")

    values = {
        FIELD_PARTICIPANT_FULL_NAME: get_participant_full_name(user),
        FIELD_PROGRAM_TITLE: program.name,
        FIELD_COMPLETION_DATE: timezone.localtime(program.datetime_finished).strftime(
            "%d.%m.%Y"
        ),
        FIELD_ORGANIZER_NAME: get_program_organizer_name(program),
        FIELD_CERTIFICATE_ID: certificate_display_id,
        FIELD_PROJECT_TITLE: (
            project.name if project and template.show_project_title else ""
        ),
        FIELD_TEAM_MEMBERS: (
            get_project_team_members(project)
            if project and template.show_team_members
            else ""
        ),
        FIELD_RANK: (
            f"{recipient.rating_position} место"
            if template.show_rank and recipient.rating_position
            else ""
        ),
        FIELD_SIGNER_NAME: template.signer_name or DEFAULT_SIGNER_NAME,
    }
    return render_certificate_html_from_values(
        template_data={
            "background_image": template.background_image,
            "signature_image": template.signature_image,
            "stamp_image": template.stamp_image,
            "company_logo_image": template.company_logo_image,
            "signature_position": template.signature_position,
            "stamp_position": template.stamp_position,
            "company_logo_position": template.company_logo_position,
            "font_family": template.font_family,
            "text_color": template.text_color,
            "accent_text_color": template.accent_text_color,
            "fields_positioning": template.fields_positioning,
        },
        values=values,
    )


def render_certificate_html_from_values(
    *,
    template_data: dict,
    values: dict[str, str],
) -> str:
    fields = build_rendered_fields(
        template_data=template_data,
        values=values,
    )
    assets = build_rendered_assets(template_data=template_data)
    background_image = template_data.get("background_image")
    background_url = get_renderable_file_url(background_image) if background_image else ""
    font_family = FONT_CSS_FAMILIES.get(
        template_data.get("font_family"), FONT_CSS_FAMILIES["roboto"]
    )
    default_labels = build_default_label_flags(
        template_data=template_data,
        values=values,
    )

    return render_to_string(
        "certificates/certificate.html",
        {
            "background_url": background_url,
            "uses_default_background": not bool(background_url),
            "has_company_logo": bool(template_data.get("company_logo_image")),
            **default_labels,
            "font_family": font_family,
            "fields": fields,
            "assets": assets,
        },
    )


def build_default_label_flags(*, template_data: dict, values: dict[str, str]) -> dict:
    positioning = normalize_fields_positioning(template_data.get("fields_positioning"))
    return {
        "show_completion_date_label": bool(
            positioning.get(FIELD_COMPLETION_DATE, {}).get("visible")
            and values.get(FIELD_COMPLETION_DATE)
        ),
        "show_certificate_id_label": bool(
            positioning.get(FIELD_CERTIFICATE_ID, {}).get("visible")
            and values.get(FIELD_CERTIFICATE_ID)
        ),
    }


def build_rendered_fields(
    *,
    template_data: dict,
    values: dict[str, str],
) -> list[dict[str, str]]:
    positioning = normalize_fields_positioning(template_data.get("fields_positioning"))
    text_color = template_data.get("text_color") or "#1A1A1A"
    accent_color = template_data.get("accent_text_color") or text_color
    rendered_fields = []

    for field_key, config in positioning.items():
        if not isinstance(config, dict) or not config.get("visible", False):
            continue

        value = values.get(field_key)
        if not value:
            continue

        color = config.get("color")
        if not color and field_key in {FIELD_PARTICIPANT_FULL_NAME, FIELD_PROGRAM_TITLE}:
            color = accent_color
        color = color or text_color
        align = config.get("align", "center")
        translate = {
            "left": "translate(0, -50%)",
            "center": "translate(-50%, -50%)",
            "right": "translate(-100%, -50%)",
        }.get(align, "translate(-50%, -50%)")

        if field_key == FIELD_PROJECT_TITLE:
            label_y = max(float(config.get("y", 0.5)) - 0.04, 0)
            label_size = max(float(config.get("font_size", 18)) * 0.62, 9)
            rendered_fields.append(
                {
                    "value": "Проект",
                    "class_name": "certificate-field--project-label",
                    "style": (
                        f"left: {float(config.get('x', 0.5)) * 100:.4f}%; "
                        f"top: {label_y * 100:.4f}%; "
                        "transform: translate(-50%, -50%); "
                        f"font-size: {label_size:.2f}px; "
                        "text-align: center; "
                        f"color: {conditional_escape(color)};"
                    ),
                }
            )

        rendered_fields.append(
            {
                "value": value,
                "class_name": "",
                "style": (
                    f"left: {float(config.get('x', 0.5)) * 100:.4f}%; "
                    f"top: {float(config.get('y', 0.5)) * 100:.4f}%; "
                    f"transform: {translate}; "
                    f"font-size: {float(config.get('font_size', 18)):.2f}px; "
                    f"text-align: {conditional_escape(align)}; "
                    f"color: {conditional_escape(color)};"
                ),
            }
        )
    return rendered_fields


def build_rendered_assets(*, template_data: dict) -> list[dict[str, str]]:
    assets = []
    signature_image = template_data.get("signature_image")
    stamp_image = template_data.get("stamp_image")
    company_logo_image = template_data.get("company_logo_image")
    signature_position = normalize_asset_position(
        template_data.get("signature_position"),
        DEFAULT_SIGNATURE_POSITION,
    )
    stamp_position = normalize_asset_position(
        template_data.get("stamp_position"),
        DEFAULT_STAMP_POSITION,
    )
    company_logo_position = normalize_asset_position(
        template_data.get("company_logo_position"),
        DEFAULT_COMPANY_LOGO_POSITION,
    )

    if company_logo_image:
        assets.append(
            {
                "url": get_renderable_file_url(company_logo_image),
                "alt": "Company logo",
                "class_name": "certificate-asset--company-logo",
                "style": (
                    f"left: {float(company_logo_position['x']) * 100:.4f}%; "
                    f"top: {float(company_logo_position['y']) * 100:.4f}%; "
                    f"width: {float(company_logo_position['width']) * 100:.4f}%; "
                    "transform: translate(-50%, -50%);"
                ),
            }
        )

    if signature_image:
        assets.append(
            {
                "url": get_renderable_file_url(signature_image),
                "alt": "Signature",
                "class_name": "certificate-asset--signature",
                "style": (
                    f"left: {float(signature_position['x']) * 100:.4f}%; "
                    f"top: {float(signature_position['y']) * 100:.4f}%; "
                    f"width: {float(signature_position['width']) * 100:.4f}%; "
                    "transform: translate(-50%, -50%);"
                ),
            }
        )

    if stamp_image:
        assets.append(
            {
                "url": get_renderable_file_url(stamp_image),
                "alt": "Stamp",
                "class_name": "certificate-asset--stamp",
                "style": (
                    f"left: {float(stamp_position['x']) * 100:.4f}%; "
                    f"top: {float(stamp_position['y']) * 100:.4f}%; "
                    f"width: {float(stamp_position['width']) * 100:.4f}%; "
                    "transform: translate(-50%, -50%);"
                ),
            }
        )

    return assets


def render_pdf_bytes(html: str) -> bytes:
    return HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()


def get_renderable_file_url(user_file: UserFile) -> str:
    local_path = get_local_media_path(user_file.link)
    if local_path and local_path.exists():
        return local_path.as_uri()
    return user_file.link


def upload_certificate_pdf(
    *,
    pdf_bytes: bytes,
    program: PartnerProgram,
    user_id: int,
    certificate_id: str,
):
    filename = f"certificate_{program.id}_{user_id}_{certificate_id}.pdf"
    uploaded_file = SimpleUploadedFile(
        filename,
        pdf_bytes,
        content_type="application/pdf",
    )
    User = get_user_model()
    owner = User.objects.get(pk=user_id)
    return CDN(storage=get_default_storage()).upload(uploaded_file, owner)


def get_project_team_members(project) -> str:
    members: list[str] = []
    seen_ids: set[int] = set()

    owner = getattr(project, "owner", None) or getattr(project, "leader", None)
    if owner:
        leader_name = get_participant_full_name(owner)
        if leader_name:
            members.append(leader_name)
        if owner.id:
            seen_ids.add(owner.id)

    collaborators = (
        project.collaborator_set.select_related("user").all()
        if hasattr(project, "collaborator_set")
        else []
    )
    for collaborator in collaborators:
        user = getattr(collaborator, "user", None)
        if not user or user.id in seen_ids:
            continue
        user_name = get_participant_full_name(user)
        if user_name:
            members.append(user_name)
        seen_ids.add(user.id)

    return ", ".join(members)


def get_program_organizer_name(program: PartnerProgram) -> str:
    company = getattr(program, "company", None)
    if company and company.name:
        return company.name
    manager = program.managers.order_by("id").first()
    if manager:
        return get_participant_full_name(manager)
    return "PROCOLLAB"


def get_certificate_stats(program: PartnerProgram) -> dict:
    try:
        recipients = get_certificate_recipients(program)
        eligible_count = len(recipients)
    except ProgramCertificateTemplate.DoesNotExist:
        eligible_count = 0

    generated_count = IssuedCertificate.objects.filter(
        program=program,
        status=IssuedCertificate.STATUS_GENERATED,
    ).count()
    last_run = CertificateGenerationRun.objects.filter(program=program).first()
    return {
        "issued_count": generated_count,
        "generated_count": generated_count,
        "pending_count": max(eligible_count - generated_count, 0),
        "eligible_count": eligible_count,
        "error_count": last_run.error_count if last_run else 0,
        "last_run": last_run,
    }


def is_certificate_released_for_participant(
    *,
    program: PartnerProgram,
    template: ProgramCertificateTemplate,
    now=None,
) -> bool:
    now = now or timezone.now()
    if template.release_mode == RELEASE_MODE_AFTER_PROGRAM_END:
        return bool(program.datetime_finished and now >= program.datetime_finished)
    if template.release_mode == RELEASE_MODE_MANUAL:
        return template.released_at is not None
    return False


def get_participant_certificate_state(
    *,
    program: PartnerProgram,
    user,
) -> dict:
    try:
        template = program.certificate_template
    except ProgramCertificateTemplate.DoesNotExist:
        return {"state": "unavailable", "certificate": None, "settings": None}

    settings_payload = {
        "is_enabled": template.is_enabled,
        "release_mode": template.release_mode,
        "released_at": template.released_at,
        "show_project_title": template.show_project_title,
    }
    if not template.is_enabled:
        return {
            "state": "unavailable",
            "certificate": None,
            "settings": settings_payload,
        }

    certificate = (
        IssuedCertificate.objects.select_related(
            "pdf_file",
            "user",
            "program_project",
            "program_project__project",
        )
        .filter(
            program=program,
            user=user,
            status=IssuedCertificate.STATUS_GENERATED,
        )
        .first()
    )
    if certificate is None:
        return {
            "state": "unavailable",
            "certificate": None,
            "settings": settings_payload,
        }

    if template.release_mode == RELEASE_MODE_AFTER_PROGRAM_END:
        if not is_certificate_released_for_participant(program=program, template=template):
            return {
                "state": "scheduled",
                "available_at": program.datetime_finished,
                "certificate": None,
                "settings": settings_payload,
            }
    elif template.release_mode == RELEASE_MODE_MANUAL and not template.released_at:
        return {
            "state": "not_released",
            "certificate": None,
            "settings": settings_payload,
        }

    return {
        "state": "available",
        "certificate": certificate,
        "settings": settings_payload,
    }


def read_user_file_bytes(user_file: UserFile) -> tuple[bytes, str, str]:
    local_path = get_local_media_path(user_file.link)
    filename = f"{user_file.name}.{user_file.extension}".strip(".")
    content_type = user_file.mime_type or "application/octet-stream"

    if local_path and local_path.exists():
        return local_path.read_bytes(), filename, content_type

    response = requests.get(user_file.link, timeout=10)
    response.raise_for_status()
    return response.content, filename, content_type


def build_certificate_verification_url(certificate_uuid) -> str:
    public_base_url = getattr(settings, "FRONTEND_URL", "https://procollab.ru").rstrip(
        "/"
    )
    return f"{public_base_url}/certificates/verify/{certificate_uuid}/"


def send_certificate_ready_notifications(certificate: IssuedCertificate) -> int:
    return 0


def get_participant_full_name(user) -> str:
    if not user:
        return ""
    parts = [user.last_name, user.first_name, getattr(user, "patronymic", "")]
    full_name = " ".join(part for part in parts if part).strip()
    if not full_name and hasattr(user, "get_full_name"):
        full_name = user.get_full_name()
    return full_name or user.email


def complete_program(program: PartnerProgram, *, author=None) -> bool:
    if program.status == "completed":
        return False

    program.status = "completed"
    program.draft = False
    program.save(update_fields=["status", "draft"])
    return True
