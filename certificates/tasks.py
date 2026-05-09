import logging

from django.utils import timezone

from certificates.enums import RELEASE_MODE_AFTER_PROGRAM_END
from certificates.models import CertificateGenerationRun, ProgramCertificateTemplate
from certificates.services import (
    complete_program,
    generate_certificate_for_user,
    generate_certificates_for_program_sync,
)
from partner_programs.models import PartnerProgram
from procollab.celery import app

logger = logging.getLogger(__name__)


@app.task(name="certificates.tasks.complete_finished_programs")
def complete_finished_programs() -> int:
    now = timezone.now()
    completed_count = 0
    programs = PartnerProgram.objects.filter(
        status="published",
        datetime_finished__lte=now,
    )
    for program in programs:
        if complete_program(program):
            completed_count += 1
    return completed_count


@app.task(name="certificates.tasks.generate_certificates_for_program")
def generate_certificates_for_program(program_id: int) -> int:
    try:
        program = PartnerProgram.objects.select_related("certificate_template").get(
            pk=program_id
        )
    except PartnerProgram.DoesNotExist:
        return 0

    try:
        template = program.certificate_template
    except ProgramCertificateTemplate.DoesNotExist:
        run = CertificateGenerationRun.objects.create(
            program=program,
            status=CertificateGenerationRun.STATUS_SKIPPED,
            error_message="Certificate template was not configured.",
            completed_at=timezone.now(),
        )
        return run.issued_count

    if not template.is_enabled or template.release_mode != RELEASE_MODE_AFTER_PROGRAM_END:
        run = CertificateGenerationRun.objects.create(
            program=program,
            status=CertificateGenerationRun.STATUS_SKIPPED,
            error_message="Certificates are disabled or not configured for auto release.",
            completed_at=timezone.now(),
        )
        return run.issued_count

    try:
        run = generate_certificates_for_program_sync(program, regenerate=True)
        return run.issued_count
    except Exception as exc:
        logger.exception("Certificate generation failed for program_id=%s", program_id)
        run = CertificateGenerationRun.objects.create(
            program=program,
            status=CertificateGenerationRun.STATUS_FAILED,
            error_message=str(exc),
            completed_at=timezone.now(),
        )
        raise


@app.task(
    bind=True,
    name="certificates.tasks.generate_single_certificate",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def generate_single_certificate(
    self, program_id: int, user_id: int, run_id: int | None = None
):
    try:
        certificate = generate_certificate_for_user(
            program_id=program_id,
            user_id=user_id,
            run_id=run_id,
        )
    except Exception:
        logger.exception(
            "Single certificate generation failed: program_id=%s user_id=%s",
            program_id,
            user_id,
        )
        raise

    return certificate.id if certificate else None
