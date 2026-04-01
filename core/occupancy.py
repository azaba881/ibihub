"""Indicateurs d’occupation pour le tableau de bord propriétaire."""

from calendar import monthrange
from datetime import date, timedelta

from django.utils import timezone

from .models import Entrepot, Reservation


def _prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def owner_occupancy_chart_data(user, months_back: int = 6) -> tuple[list[str], list[float]]:
    """
    Pour chaque mois : (jours occupés) / (nb entrepôts × jours du mois) × 100.
    Un jour est « occupé » pour un entrepôt s’il existe une réservation active ce jour-là.
    """
    if getattr(user, 'role', None) != 'OWNER':
        return [], []

    entrepots = list(Entrepot.objects.filter(proprietaire=user))
    if not entrepots:
        return [], []

    today = timezone.now().date()
    cy, cm = today.year, today.month
    months_order: list[tuple[int, int]] = []
    for _ in range(months_back):
        months_order.insert(0, (cy, cm))
        cy, cm = _prev_month(cy, cm)

    labels: list[str] = []
    ratios: list[float] = []
    n = len(entrepots)
    active_statuses = [
        Reservation.Statut.EN_ATTENTE,
        Reservation.Statut.CONFIRME,
        Reservation.Statut.TERMINE,
    ]

    for y, m in months_order:
        dim = monthrange(y, m)[1]
        total_slots = n * dim
        occupied = 0
        d0 = date(y, m, 1)
        for offset in range(dim):
            d = d0 + timedelta(days=offset)
            for e in entrepots:
                if e.reservations.filter(
                    statut__in=active_statuses,
                    date_debut__lte=d,
                    date_fin__gte=d,
                ).exists():
                    occupied += 1
        pct = (occupied / total_slots * 100) if total_slots else 0.0
        labels.append(f'{m:02d}/{y}')
        ratios.append(round(pct, 1))

    return labels, ratios
