import logging

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ParrainageGain, Reservation, UserCustom
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


@receiver(post_save, sender=Reservation)
def reward_referral_on_completed_reservation(sender, instance, created, **kwargs):
    if instance.statut != Reservation.Statut.TERMINE:
        return
    if instance.gain_parrainage_verse:
        return
    client = instance.client
    if not client or not client.parrain_id:
        return
    try:
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().select_related('client').get(
                pk=instance.pk
            )
            if reservation.gain_parrainage_verse or reservation.statut != Reservation.Statut.TERMINE:
                return
            # Récompense uniquement à la première réservation terminée du filleul.
            has_previous_completed = Reservation.objects.filter(
                client_id=reservation.client_id,
                statut=Reservation.Statut.TERMINE,
            ).exclude(pk=reservation.pk).exists()
            if has_previous_completed:
                reservation.gain_parrainage_verse = True
                reservation.save(update_fields=['gain_parrainage_verse'])
                return
            amount = 500
            UserCustom.objects.filter(pk=reservation.client.parrain_id).update(
                solde_parrainage=F('solde_parrainage') + amount
            )
            ParrainageGain.objects.create(
                parrain_id=reservation.client.parrain_id,
                filleul_id=reservation.client_id,
                reservation_id=reservation.pk,
                montant=amount,
            )
            reservation.gain_parrainage_verse = True
            reservation.save(update_fields=['gain_parrainage_verse'])
    except Exception:
        logger.exception('Parrainage reward failed for reservation %s', instance.pk)


@receiver(post_save, sender=UserCustom)
def ensure_referral_code_for_user(sender, instance, created, **kwargs):
    if instance.code_parrainage:
        return
    try:
        code = instance._generate_referral_code()
        UserCustom.objects.filter(pk=instance.pk, code_parrainage__isnull=True).update(
            code_parrainage=code
        )
    except Exception:
        logger.exception('Unable to generate referral code for user %s', instance.pk)
