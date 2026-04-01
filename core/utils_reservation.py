"""Règles métier liées aux réservations (édition d’espace, calendrier, blocages)."""

from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import EntrepotPeriodeBloquee, Reservation


def entrepot_has_blocking_reservations(entrepot) -> bool:
    """
    True si l’espace ne doit pas être modifié : réservation en attente (legacy),
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


def _reservation_ranges_qs(entrepot):
    return entrepot.reservations.filter(
        statut__in=[
            Reservation.Statut.EN_ATTENTE,
            Reservation.Statut.CONFIRME,
        ]
    ).values_list('date_debut', 'date_fin')


def _blocage_ranges_qs(entrepot):
    return EntrepotPeriodeBloquee.objects.filter(entrepot=entrepot).values_list(
        'date_debut', 'date_fin'
    )


def entrepot_blocked_date_ranges_iso(entrepot):
    """
    Périodes indisponibles : réservations (en attente / confirmées) + verrous admin.
    Chaque entrée : {'debut': 'Y-m-d', 'fin': 'Y-m-d', 'kind': 'reservation'|'lock'}.
    """
    out = []
    for d0, d1 in _reservation_ranges_qs(entrepot):
        out.append(
            {
                'debut': d0.isoformat(),
                'fin': d1.isoformat(),
                'kind': 'reservation',
            }
        )
    for d0, d1 in _blocage_ranges_qs(entrepot):
        out.append(
            {
                'debut': d0.isoformat(),
                'fin': d1.isoformat(),
                'kind': 'lock',
            }
        )
    return out


def _iter_days_inclusive(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def entrepot_blocked_date_strings_iso(entrepot):
    """Liste triée de dates 'Y-m-d' pour Flatpickr (disable)."""
    seen = set()
    for item in entrepot_blocked_date_ranges_iso(entrepot):
        a = date.fromisoformat(item['debut'])
        b = date.fromisoformat(item['fin'])
        for d in _iter_days_inclusive(a, b):
            seen.add(d.isoformat())
    return sorted(seen)


def booking_range_unavailable(entrepot, date_debut: date, date_fin: date) -> bool:
    """True si la plage chevauche une réservation active ou une période bloquée."""
    if date_fin < date_debut:
        return True
    res = entrepot.reservations.filter(
        statut__in=[
            Reservation.Statut.EN_ATTENTE,
            Reservation.Statut.CONFIRME,
        ],
        date_debut__lte=date_fin,
        date_fin__gte=date_debut,
    ).exists()
    if res:
        return True
    return EntrepotPeriodeBloquee.objects.filter(
        entrepot=entrepot,
        date_debut__lte=date_fin,
        date_fin__gte=date_debut,
    ).exists()
