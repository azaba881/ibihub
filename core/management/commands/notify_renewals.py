from datetime import timedelta

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Reservation


class Command(BaseCommand):
    help = "Notifie les reservations mensuelles a renouveler J-3."

    def handle(self, *args, **options):
        target_date = timezone.now().date() + timedelta(days=3)
        qs = Reservation.objects.select_related('client', 'entrepot', 'entrepot__proprietaire').filter(
            type_paiement=Reservation.TypePaiement.MENSUEL,
            prochaine_echeance=target_date,
            statut=Reservation.Statut.CONFIRME,
        )
        sent = 0
        for r in qs:
            recipients = [r.client.email or r.client.username]
            owner_mail = r.entrepot.proprietaire.email or r.entrepot.proprietaire.username
            if owner_mail:
                recipients.append(owner_mail)
            send_mail(
                subject=f"[IbiHub] Rappel renouvellement réservation #{r.pk}",
                message=(
                    f"La réservation #{r.pk} arrive à échéance le {r.prochaine_echeance:%d/%m/%Y}. "
                    "Merci de préparer le renouvellement."
                ),
                from_email=None,
                recipient_list=[m for m in recipients if m],
                fail_silently=True,
            )
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"{sent} notification(s) envoyée(s)."))
