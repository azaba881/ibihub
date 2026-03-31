from django.urls import reverse
from django.utils import timezone

from .models import Reservation


def dashboard_notifications(request):
    """Compteur et aperçu pour la cloche du tableau de bord."""
    if not request.user.is_authenticated:
        return {}

    user = request.user
    items = []
    count = 0

    if getattr(user, 'role', None) == 'OWNER':
        pending = (
            Reservation.objects.filter(
                entrepot__proprietaire=user,
                statut=Reservation.Statut.EN_ATTENTE,
            )
            .select_related('entrepot')
            .order_by('-date_debut')[:8]
        )
        count = Reservation.objects.filter(
            entrepot__proprietaire=user,
            statut=Reservation.Statut.EN_ATTENTE,
        ).count()
        for r in pending:
            items.append(
                {
                    'text': f'{r.entrepot.titre} — du {r.date_debut.strftime("%d/%m/%Y")}',
                    'url': reverse('core:dashboard_reservations'),
                }
            )
    else:
        today = timezone.now().date()
        upcoming = (
            Reservation.objects.filter(
                client=user,
                statut__in=[
                    Reservation.Statut.EN_ATTENTE,
                    Reservation.Statut.CONFIRME,
                ],
                date_fin__gte=today,
            )
            .select_related('entrepot')
            .order_by('date_debut')[:8]
        )
        count = upcoming.count()
        for r in upcoming:
            items.append(
                {
                    'text': f'{r.entrepot.titre} — {r.date_debut.strftime("%d/%m/%Y")}',
                    'url': reverse('core:dashboard_reservations'),
                }
            )

    return {
        'dashboard_notif_count': count,
        'dashboard_notif_items': items,
    }
