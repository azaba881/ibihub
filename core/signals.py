import logging

from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Reservation
from .pdf_contract import (
    render_reservation_contract_pdf_bytes,
    render_reservation_ticket_pdf_bytes,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Reservation)
def generate_reservation_contract_pdf(sender, instance, created, **kwargs):
    if instance.statut != Reservation.Statut.CONFIRME:
        return
    if (
        instance.contrat_pdf
        and instance.contrat_pdf.name
        and instance.ticket_pdf
        and instance.ticket_pdf.name
    ):
        return
    try:
        pdf_bytes = render_reservation_contract_pdf_bytes(instance)
        ticket_bytes = render_reservation_ticket_pdf_bytes(instance)
    except Exception:
        logger.exception('Contrat PDF reservation %s', instance.pk)
        return
    name = f'contrat_reservation_{instance.pk}.pdf'
    ticket_name = f'ticket_reservation_{instance.pk}.pdf'
    instance.contrat_pdf.save(name, ContentFile(pdf_bytes), save=False)
    instance.ticket_pdf.save(ticket_name, ContentFile(ticket_bytes), save=False)
    Reservation.objects.filter(pk=instance.pk).update(
        contrat_pdf=instance.contrat_pdf.name,
        ticket_pdf=instance.ticket_pdf.name,
    )
