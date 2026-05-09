from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from certificates.enums import RELEASE_MODE_AFTER_PROGRAM_END
from certificates.models import ProgramCertificateTemplate
from partner_programs.models import PartnerProgram


@receiver(pre_save, sender=PartnerProgram)
def remember_previous_program_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._certificate_previous_status = None
        return

    try:
        instance._certificate_previous_status = (
            sender.objects.only("status").get(pk=instance.pk).status
        )
    except sender.DoesNotExist:
        instance._certificate_previous_status = None


@receiver(post_save, sender=PartnerProgram)
def generate_certificates_after_program_completion(sender, instance, created, **kwargs):
    previous_status = getattr(instance, "_certificate_previous_status", None)
    if created:
        return
    if instance.status != "completed" or previous_status == "completed":
        return

    try:
        template = instance.certificate_template
    except ProgramCertificateTemplate.DoesNotExist:
        return

    if not template.is_enabled or template.release_mode != RELEASE_MODE_AFTER_PROGRAM_END:
        return

    from certificates.tasks import generate_certificates_for_program

    generate_certificates_for_program.delay(instance.id)
