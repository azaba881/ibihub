"""Règles métier liées aux réservations (édition d’espace, calendrier)."""

from django.db.models import Q
from django.utils import timezone

from .models import Reservation


def entrepot_has_blocking_reservations(entrepot) -> bool:
    """
    True si l’espace ne doit pas être modifié : réservation en attente,
    ou réservation confirmée dont la période n’est pas entièrement passée.
    """
    today = timezone.now().date()
    return entrepot.reservations.filter(
        Q(statut=Reservation.Statut.EN_ATTENTE)
        | Q(
            statut=Reservation.Statut.CONFIRME,
            date_fin__gte=today,
        )
    ).exists()


def entrepot_blocked_date_ranges_iso(entrepot):
    """
    Périodes indisponibles pour l’affichage calendrier (EN_ATTENTE ou CONFIRME).
    Liste de dicts {'debut': 'Y-m-d', 'fin': 'Y-m-d'} inclusives.
    """
    qs = entrepot.reservations.filter(
        statut__in=[
            Reservation.Statut.EN_ATTENTE,
            Reservation.Statut.CONFIRME,
        ]
    ).values_list('date_debut', 'date_fin')
    return [
        {'debut': d0.isoformat(), 'fin': d1.isoformat()}
        for d0, d1 in qs
    ]
