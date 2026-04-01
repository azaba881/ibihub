import base64
import io
import json
import random
from datetime import datetime
from datetime import timedelta
from decimal import Decimal, InvalidOperation

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from .forms import (
    RECLAMATION_TYPE_CHOICES,
    ContactForm,
    EntrepotIndisponibiliteForm,
    EtatDesLieuxForm,
    EntrepotAvisForm,
    EntrepotForm,
    IbiHubAuthenticationForm,
    LitigeForm,
    OwnerKycForm,
    ReclamationForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import (
    CategorieStorage,
    Entrepot,
    EntrepotAvis,
    EntrepotIndisponibilite,
    EtatDesLieux,
    EntrepotImage,
    Favori,
    Litige,
    ParrainageGain,
    Reservation,
    UserCustom,
)
from .occupancy import owner_occupancy_chart_data
from .utils_reservation import (
    booking_range_unavailable,
    entrepot_blocked_date_ranges_iso,
    entrepot_blocked_date_strings_iso,
    entrepot_has_blocking_reservations,
)


def user_has_owner_access(user) -> bool:
    return bool(user.is_authenticated and (user.role == 'OWNER' or user.can_post_announcements))


def get_dashboard_mode(request, user) -> str:
    if not user.is_authenticated:
        return 'MERCHANT'
    asked = (request.session.get('dashboard_mode') or '').upper()
    if asked in {'MERCHANT', 'OWNER'}:
        mode = asked
    else:
        mode = 'OWNER' if user.role == 'OWNER' else 'MERCHANT'
    if mode == 'OWNER' and not user_has_owner_access(user):
        mode = 'MERCHANT'
    request.session['dashboard_mode'] = mode
    return mode


def home(request):
    qs = CategorieStorage.objects.annotate(nb=Count('entrepots'))
    categories_all = qs.order_by('nom')
    pool = list(qs)
    if pool:
        n = len(pool)
        categories_banner = random.sample(pool, min(3, n))
        categories_explore = random.sample(pool, min(6, n))
    else:
        categories_banner = []
        categories_explore = []
    # 6 espaces publiés (disponibles + propriétaire vérifié)
    entrepot_qs = Entrepot.objects.filter(
        disponible=True,
        proprietaire__is_verified=True,
    ).select_related('categorie', 'proprietaire').order_by('-is_boosted', '-created_at')
    ids = list(entrepot_qs.values_list('pk', flat=True))
    if not ids:
        recent_entrepots = []
    else:
        k = min(6, len(ids))
        picked = random.sample(ids, k)
        recent_entrepots = list(entrepot_qs.filter(pk__in=picked))
        order = {pk: i for i, pk in enumerate(picked)}
        recent_entrepots.sort(key=lambda e: order[e.pk])
    return render(
        request,
        'public/home.html',
        {
            'categories_all': categories_all,
            'categories_banner': categories_banner,
            'categories_explore': categories_explore,
            'recent_entrepots': recent_entrepots,
        },
    )


def liste_espaces(request):
    entrepots = (
        Entrepot.objects.filter(disponible=True, proprietaire__is_verified=True)
        .select_related('categorie', 'proprietaire')
        .order_by('-is_boosted', '-created_at')
    )

    q = (request.GET.get('q') or '').strip()
    ville = (request.GET.get('ville') or '').strip()
    prix_max_raw = (request.GET.get('prix_max') or '').strip()
    categorie_id = (request.GET.get('categorie') or '').strip()

    if q:
        entrepots = entrepots.filter(
            Q(titre__icontains=q)
            | Q(adresse__icontains=q)
            | Q(description_detaillee__icontains=q)
            | Q(categorie__nom__icontains=q)
        )

    if ville:
        # Correspondance souple (saisie libre hero / fautes de frappe) ; les valeurs en base sont les libellés Ville
        entrepots = entrepots.filter(ville__icontains=ville)

    if prix_max_raw:
        try:
            prix_max = Decimal(prix_max_raw.replace(',', '.').strip())
            if prix_max >= 0:
                entrepots = entrepots.filter(prix_par_jour__lte=prix_max)
        except (InvalidOperation, ValueError):
            pass

    if categorie_id.isdigit():
        entrepots = entrepots.filter(categorie_id=int(categorie_id))

    categories = CategorieStorage.objects.all().order_by('nom')

    paginator = Paginator(entrepots, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(
        request,
        'public/espaces.html',
        {
            'entrepots': page_obj.object_list,
            'page_obj': page_obj,
            'filtres': {
                'q': q,
                'ville': ville,
                'prix_max': prix_max_raw,
                'categorie': categorie_id,
            },
            'categories': categories,
            'villes_choices': Entrepot.Ville.choices,
        },
    )


def a_propos(request):
    return render(request, 'public/about.html')


def opportunites_immobilieres(request):
    return render(request, 'public/opportunites-immobilieres.html')


def _send_welcome_email(user):
    email_to = (user.email or user.username or '').strip()
    if not email_to:
        return
    ctx = {
        'user': user,
        'dashboard_url': '/dashboard/',
    }
    html_body = render_to_string('emails/welcome_user.html', ctx)
    text_body = render_to_string('emails/welcome_user.txt', ctx)
    msg = EmailMultiAlternatives(
        subject='Bienvenue sur IbiHub',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email_to],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=True)


def _send_reservation_confirmation_email(reservation, request=None):
    email_to = (reservation.client.email or reservation.client.username or '').strip()
    if not email_to:
        return
    ticket_url = ''
    if request is not None:
        try:
            ticket_url = request.build_absolute_uri(
                reverse('core:reservation_ticket_pdf', kwargs={'pk': reservation.pk})
            )
        except Exception:
            ticket_url = ''
    ctx = {
        'reservation': reservation,
        'dashboard_url': '/dashboard/reservations/',
        'ticket_url': ticket_url,
    }
    html_body = render_to_string('emails/reservation_confirmation_user.html', ctx)
    text_body = render_to_string('emails/reservation_confirmation_user.txt', ctx)
    msg = EmailMultiAlternatives(
        subject=f"[IbiHub] Réservation confirmée #{reservation.pk}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email_to],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=True)

    invoice_html = render_to_string('email/invoice.html', ctx)
    invoice_text = render_to_string('emails/invoice.txt', ctx)
    invoice_msg = EmailMultiAlternatives(
        subject=f"[IbiHub] Facture réservation #{reservation.pk}",
        body=invoice_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email_to],
    )
    invoice_msg.attach_alternative(invoice_html, 'text/html')
    if reservation.ticket_pdf and reservation.ticket_pdf.name:
        try:
            reservation.ticket_pdf.open('rb')
            invoice_msg.attach(
                f"facture-ibihub-reservation-{reservation.pk}.pdf",
                reservation.ticket_pdf.read(),
                'application/pdf',
            )
            reservation.ticket_pdf.close()
        except OSError:
            pass
    invoice_msg.send(fail_silently=True)


@never_cache
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            ctx_mail = {
                'name': cd['name'],
                'email': cd['email'],
                'subject': cd['subject'],
                'message': cd['message'],
            }
            html_body = render_to_string('emails/contact_notification.html', ctx_mail)
            text_body = render_to_string('emails/contact_notification.txt', ctx_mail)
            recipient = getattr(
                settings,
                'CONTACT_RECIPIENT_EMAIL',
                settings.DEFAULT_FROM_EMAIL,
            )
            msg = EmailMultiAlternatives(
                subject=f'[IbiHub — Contact] {cd["subject"]}',
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                reply_to=[cd['email']],
            )
            msg.attach_alternative(html_body, 'text/html')
            try:
                msg.send(fail_silently=False)
            except Exception as exc:
                messages.error(
                    request,
                    'L’envoi du message a échoué. Réessayez plus tard ou écrivez-nous par e-mail.',
                )
                if settings.DEBUG:
                    messages.info(request, str(exc))
            else:
                return redirect('core:confirmation_contact')
    else:
        form = ContactForm()
    return render(request, 'public/contact.html', {'form': form})


def confirmation_contact(request):
    return render(request, 'public/confirmation-contact.html')


@never_cache
def reclamation(request):
    if request.method == 'POST':
        form = ReclamationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            ctx_mail = {
                'type_label': dict(RECLAMATION_TYPE_CHOICES).get(
                    cd['type_reclamation'], cd['type_reclamation']
                ),
                'reference': cd.get('reference') or '—',
                'subject': cd['subject'],
                'detail': cd['detail'],
                'name': cd['name'],
                'email': cd['email'],
                'phone': cd.get('phone') or '—',
            }
            html_body = render_to_string('emails/reclamation_notification.html', ctx_mail)
            text_body = render_to_string('emails/reclamation_notification.txt', ctx_mail)
            recipient = getattr(
                settings,
                'CONTACT_RECIPIENT_EMAIL',
                settings.DEFAULT_FROM_EMAIL,
            )
            msg = EmailMultiAlternatives(
                subject=f'[IbiHub — Réclamation] {cd["subject"]}',
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                reply_to=[cd['email']],
            )
            msg.attach_alternative(html_body, 'text/html')
            try:
                msg.send(fail_silently=False)
            except Exception as exc:
                messages.error(
                    request,
                    'L’envoi de la réclamation a échoué. Réessayez plus tard.',
                )
                if settings.DEBUG:
                    messages.info(request, str(exc))
            else:
                return redirect('core:confirmation_reclamation')
    else:
        form = ReclamationForm()
    return render(request, 'public/reclamation.html', {'form': form})


def confirmation_reclamation(request):
    return render(request, 'public/confirmation-reclamation.html')


def politique_confidentialite(request):
    return render(request, 'public/legal/confidentialite.html')


def conditions_utilisation(request):
    return render(request, 'public/legal/cgu.html')


def politique_securite_espaces(request):
    return render(request, 'public/legal/securite-espaces.html')


def confirmation_reservation(request):
    reservation = None
    rid = request.GET.get('reservation')
    if rid:
        try:
            reservation = Reservation.objects.select_related(
                'entrepot', 'client'
            ).get(pk=int(rid))
        except (ValueError, Reservation.DoesNotExist):
            pass
    return render(
        request,
        'public/confirmation-reservation.html',
        {'reservation': reservation},
    )


class IbiHubLoginView(LoginView):
    template_name = 'public/sign-in.html'
    form_class = IbiHubAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return reverse('admin:index')
        return super().get_success_url()


class SignUpView(CreateView):
    model = UserCustom
    form_class = UserRegistrationForm
    template_name = 'public/sign-up.html'

    def form_valid(self, form):
        self.object = form.save()
        login(
            self.request,
            self.object,
            backend='core.auth_backends.EmailOrPhoneBackend',
        )
        _send_welcome_email(self.object)
        if self.object.parrain_id:
            messages.success(self.request, 'Bienvenue sur IbiHub. Parrainage appliqué avec succès.')
        else:
            messages.success(self.request, 'Bienvenue sur IbiHub.')
        return HttpResponseRedirect(self.get_success_url())

    def get_initial(self):
        initial = super().get_initial()
        ref = (self.request.GET.get('ref') or '').strip()
        if ref:
            initial['parrainage_code_input'] = ref
        return initial

    def get_success_url(self):
        if self.object.role == 'OWNER':
            return reverse('core:dashboard_spaces')
        return reverse('core:mon_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:mon_dashboard')
        return super().dispatch(request, *args, **kwargs)


def qr_code_data_uri(payload: str) -> str:
    buf = io.BytesIO()
    img = qrcode.make(payload, box_size=4, border=2)
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f'data:image/png;base64,{b64}'


def _parse_reservation_dates(post) -> tuple:
    """Retourne (date_debut, date_fin) ou (None, None) si invalide."""
    raw_start = post.get('date_debut')
    raw_end = post.get('date_fin')
    if not raw_start or not raw_end:
        return None, None
    try:
        d0 = datetime.strptime(str(raw_start).strip(), '%Y-%m-%d').date()
        d1 = datetime.strptime(str(raw_end).strip(), '%Y-%m-%d').date()
    except ValueError:
        return None, None
    return d0, d1


def _push_pending_referral_notifications(request):
    if not request.user.is_authenticated:
        return
    pending = list(
        ParrainageGain.objects.filter(
            parrain=request.user,
            notified=False,
        ).select_related('filleul')[:10]
    )
    if not pending:
        return
    for gain in pending:
        label = gain.filleul.get_full_name() or gain.filleul.username
        messages.success(
            request,
            f'Félicitations ! Vous avez gagné 500 FCFA grâce à la réservation de {label}.',
        )
    ParrainageGain.objects.filter(pk__in=[g.pk for g in pending]).update(notified=True)


def _push_owner_revenue_hint(request):
    user = request.user
    if not user.is_authenticated or not user_has_owner_access(user):
        return
    pending_owner_revenue = Reservation.objects.filter(
        entrepot__proprietaire=user,
        statut=Reservation.Statut.CONFIRME,
    ).aggregate(t=Sum('revenu_net_proprietaire'))['t'] or Decimal('0')
    if pending_owner_revenue > 0:
        messages.info(
            request,
            f'Info revenus: {pending_owner_revenue:.0f} FCFA de loyers en attente.',
        )


@login_required
def mon_dashboard(request):
    _push_pending_referral_notifications(request)
    _push_owner_revenue_hint(request)
    user = request.user
    mode = get_dashboard_mode(request, user)
    ctx = {
        'is_owner': mode == 'OWNER',
        'dashboard_mode': mode,
    }
    if mode == 'OWNER' and user_has_owner_access(user):
        entrepots = Entrepot.objects.filter(proprietaire=user)
        ctx['owner_entrepot_count'] = entrepots.count()
        ca_termine = Reservation.objects.filter(
            entrepot__proprietaire=user,
            statut=Reservation.Statut.TERMINE,
        ).aggregate(t=Sum('montant_total'))['t']
        ctx['owner_ca_termine'] = ca_termine or Decimal('0')
        revenus_confirmes = Reservation.objects.filter(
            entrepot__proprietaire=user,
            statut=Reservation.Statut.CONFIRME,
        ).aggregate(t=Sum('montant_total'))['t']
        ctx['owner_revenus_en_attente'] = revenus_confirmes or Decimal('0')
        pending = Reservation.objects.filter(
            entrepot__proprietaire=user,
            statut=Reservation.Statut.EN_ATTENTE,
        ).count()
        if pending:
            messages.info(
                request,
                (
                    f'Vous avez {pending} réservation'
                    f'{"s" if pending > 1 else ""} en attente de confirmation. '
                    f'Consultez la section « Réservations » pour les valider.'
                ),
            )
        occ_labels, occ_values = owner_occupancy_chart_data(user, months_back=6)
        ctx['owner_occupancy_labels_json'] = json.dumps(occ_labels, ensure_ascii=False)
        ctx['owner_occupancy_values_json'] = json.dumps(occ_values, ensure_ascii=False)
    else:
        today = timezone.now().date()
        actives_qs = Reservation.objects.filter(
            client=user,
            statut__in=[
                Reservation.Statut.EN_ATTENTE,
                Reservation.Statut.CONFIRME,
            ],
            date_fin__gte=today,
        )
        ctx['merchant_reservations_actives_count'] = actives_qs.count()
        depense_terminee = Reservation.objects.filter(
            client=user,
            statut=Reservation.Statut.TERMINE,
        ).aggregate(t=Sum('montant_total'))['t']
        ctx['merchant_depense_terminee'] = depense_terminee or Decimal('0')
        montant_actifs = actives_qs.aggregate(t=Sum('montant_total'))['t']
        ctx['merchant_montant_actifs'] = montant_actifs or Decimal('0')
        merchant_list = list(
            actives_qs.select_related('entrepot', 'entrepot__categorie').order_by(
                '-date_debut'
            )[:12]
        )
        for r in merchant_list:
            if r.statut == Reservation.Statut.CONFIRME and r.qr_code_auth:
                r.qr_data_uri = qr_code_data_uri(r.qr_code_auth)
            else:
                r.qr_data_uri = None
        ctx['merchant_reservations'] = merchant_list

    return render(request, 'dashboard/dashboard_user.html', ctx)


@login_required
def dashboard_owner_kyc(request):
    if not request.user.can_post_announcements and request.user.role != 'OWNER':
        request.user.can_post_announcements = True
        request.user.save(update_fields=['can_post_announcements'])
        messages.info(request, 'Mode propriétaire activé. Complétez votre KYC.')
    if request.method == 'POST':
        form = OwnerKycForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Pièce d’identité transmise. Notre équipe vérifie votre dossier sous peu.',
            )
            return redirect('core:dashboard_owner_kyc')
    else:
        form = OwnerKycForm(instance=request.user)
    return render(
        request,
        'dashboard/dashboard-kyc.html',
        {'form': form},
    )


@login_required
def dashboard_switch_mode(request):
    current = get_dashboard_mode(request, request.user)
    target = 'OWNER' if current == 'MERCHANT' else 'MERCHANT'
    if target == 'OWNER':
        if not user_has_owner_access(request.user):
            request.user.can_post_announcements = True
            request.user.save(update_fields=['can_post_announcements'])
        request.session['dashboard_mode'] = 'OWNER'
        if not request.user.is_verified:
            return redirect('core:dashboard_owner_mode_kyc_required')
        messages.success(request, 'Mode propriétaire activé.')
        return redirect('core:mon_dashboard')
    request.session['dashboard_mode'] = 'MERCHANT'
    messages.success(request, 'Mode commerçant activé.')
    return redirect('core:mon_dashboard')


@login_required
def dashboard_owner_mode_kyc_required(request):
    return render(request, 'dashboard/dashboard-owner-mode-kyc-required.html')


@login_required
def dashboard_favorites(request):
    favoris = (
        Favori.objects.filter(user=request.user)
        .select_related('entrepot', 'entrepot__categorie')
        .order_by('-created_at')
    )
    return render(request, 'dashboard/dashboard-favorites.html', {'favoris': favoris})


@login_required
@require_POST
def toggle_favori(request, pk):
    entrepot = get_object_or_404(Entrepot, pk=pk)
    fav = Favori.objects.filter(user=request.user, entrepot=entrepot)
    if fav.exists():
        fav.delete()
        messages.info(request, 'Retiré des favoris.')
    else:
        Favori.objects.create(user=request.user, entrepot=entrepot)
        messages.success(request, 'Ajouté aux favoris.')
    return redirect('core:espace_detail', pk=pk)


@login_required
def dashboard_admin_analytics(request):
    if not request.user.is_staff:
        raise PermissionDenied
    rows = list(
        Reservation.objects.filter(
            statut__in=[
                Reservation.Statut.CONFIRME,
                Reservation.Statut.TERMINE,
            ],
        )
        .annotate(month=TruncMonth('date_debut'))
        .values('month')
        .annotate(
            total_commission=Sum('frais_assurance'),
            nb_reservations=Count('id'),
        )
        .order_by('-month')[:36]
    )
    cautions = list(
        Reservation.objects.filter(montant_caution__gt=0, caution_rendue=False)
        .select_related('entrepot', 'client', 'etat_des_lieux')
        .order_by('-date_debut')[:50]
    )
    for r in cautions:
        etat = getattr(r, 'etat_des_lieux', None)
        r.can_release_caution = bool(etat and etat.sortie_complete)
    return render(
        request,
        'dashboard/dashboard-admin-analytics.html',
        {'rows': rows, 'cautions': cautions},
    )



@login_required
@require_POST
def reservation_liberer_caution(request, pk):
    if not request.user.is_staff:
        raise PermissionDenied
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.montant_caution <= 0:
        messages.info(request, 'Aucune caution à libérer pour cette réservation.')
        return redirect('core:dashboard_admin_analytics')
    if reservation.caution_rendue:
        messages.info(request, 'Cette caution est déjà marquée comme rendue.')
        return redirect('core:dashboard_admin_analytics')
    etat = getattr(reservation, 'etat_des_lieux', None)
    if not etat or not etat.sortie_complete:
        messages.error(request, 'Ajoutez les 2 photos de sortie dans l’état des lieux avant restitution.')
        return redirect('core:dashboard_admin_analytics')
    reservation.caution_rendue = True
    reservation.save(update_fields=['caution_rendue'])
    messages.success(request, f'Caution de la réservation #{reservation.pk} marquée comme rendue.')
    return redirect('core:dashboard_admin_analytics')

@login_required
def reservation_contrat_download(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
    )
    is_owner_of_space = reservation.entrepot.proprietaire_id == request.user.id
    is_client = reservation.client_id == request.user.id
    if not (is_owner_of_space or is_client):
        raise PermissionDenied
    if not reservation.contrat_pdf or not reservation.contrat_pdf.name:
        messages.error(
            request,
            'Le contrat PDF n’est pas encore disponible (réservation non confirmée ou génération en cours).',
        )
        return redirect('core:dashboard_reservations')
    try:
        fh = reservation.contrat_pdf.open('rb')
    except OSError:
        messages.error(request, 'Impossible de lire le fichier contrat.')
        return redirect('core:dashboard_reservations')
    return FileResponse(
        fh,
        as_attachment=True,
        filename=f'contrat_ibihub_reservation_{reservation.pk}.pdf',
    )


@login_required
def reservation_ticket_download(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
    )
    is_owner_of_space = reservation.entrepot.proprietaire_id == request.user.id
    is_client = reservation.client_id == request.user.id
    if not (is_owner_of_space or is_client):
        raise PermissionDenied
    if not reservation.ticket_pdf or not reservation.ticket_pdf.name:
        messages.error(request, 'Le ticket PDF n’est pas encore disponible.')
        return redirect('core:dashboard_reservations')
    try:
        fh = reservation.ticket_pdf.open('rb')
    except OSError:
        messages.error(request, 'Impossible de lire le ticket.')
        return redirect('core:dashboard_reservations')
    return FileResponse(
        fh,
        as_attachment=True,
        filename=f'ticket_ibihub_reservation_{reservation.pk}.pdf',
    )


@login_required
def dashboard_spaces(request):
    _push_pending_referral_notifications(request)
    _push_owner_revenue_hint(request)
    if not user_has_owner_access(request.user):
        messages.info(request, 'La gestion des espaces est réservée aux propriétaires.')
        return redirect('core:mon_dashboard')
    entrepots = list(
        Entrepot.objects.filter(proprietaire=request.user).select_related('categorie')
    )
    for e in entrepots:
        e.can_owner_edit = not entrepot_has_blocking_reservations(e)
    return render(
        request,
        'dashboard/dashboard-spaces.html',
        {'entrepots': entrepots},
    )


@login_required
def dashboard_referral(request):
    _push_pending_referral_notifications(request)
    share_url = request.build_absolute_uri(reverse('core:sign_up'))
    share_text = (
        f"Rejoins IbiHub avec mon code {request.user.code_parrainage} : {share_url}"
    )
    return render(
        request,
        'dashboard/dashboard-referral.html',
        {
            'referral_code': request.user.code_parrainage,
            'share_text': share_text,
            'share_link_direct': request.build_absolute_uri(
                f"{reverse('core:sign_up')}?ref={request.user.code_parrainage}"
            ),
        },
    )


@login_required
def dashboard_billing(request):
    return redirect(f"{reverse('core:dashboard_settings')}?tab=billing")


@login_required
def activate_owner_mode(request):
    if request.user.role == 'OWNER' or request.user.can_post_announcements:
        return redirect('core:dashboard_owner_kyc')
    request.user.can_post_announcements = True
    request.user.save(update_fields=['can_post_announcements'])
    messages.success(
        request,
        'Mode propriétaire activé. Complétez le formulaire KYC pour publier vos annonces.',
    )
    return redirect('core:dashboard_owner_kyc')


@login_required
def dashboard_disponibilites(request):
    if not user_has_owner_access(request.user):
        raise PermissionDenied
    if request.method == 'POST':
        form = EntrepotIndisponibiliteForm(request.POST)
        form.fields['entrepot'].queryset = Entrepot.objects.filter(proprietaire=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.entrepot = form.cleaned_data['entrepot']
            item.save()
            messages.success(request, 'Période indisponible enregistrée.')
            return redirect('core:dashboard_disponibilites')
    else:
        form = EntrepotIndisponibiliteForm()
        form.fields['entrepot'].queryset = Entrepot.objects.filter(proprietaire=request.user)
    indispos_qs = EntrepotIndisponibilite.objects.filter(
        entrepot__proprietaire=request.user
    ).select_related('entrepot').order_by('-date_debut')
    paginator = Paginator(indispos_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(
        request,
        'dashboard/dashboard-disponibilites.html',
        {'form': form, 'indispos': page_obj.object_list, 'page_obj': page_obj},
    )


@login_required
@require_POST
def dashboard_disponibilites_delete(request, pk):
    if not user_has_owner_access(request.user):
        raise PermissionDenied
    indispo = get_object_or_404(
        EntrepotIndisponibilite.objects.select_related('entrepot'),
        pk=pk,
        entrepot__proprietaire=request.user,
    )
    indispo.delete()
    messages.success(request, 'Indisponibilité supprimée.')
    return redirect('core:dashboard_disponibilites')


@login_required
@require_POST
def entrepot_boost_activate(request, pk):
    if not user_has_owner_access(request.user):
        raise PermissionDenied
    entrepot = get_object_or_404(Entrepot, pk=pk, proprietaire=request.user)
    entrepot.is_boosted = True
    entrepot.boost_expires_at = timezone.now() + timedelta(days=7)
    entrepot.save(update_fields=['is_boosted', 'boost_expires_at'])
    messages.success(request, f"L'espace #{entrepot.pk} est boosté pour 7 jours.")
    return redirect('core:dashboard_spaces')


class EntrepotCreateView(LoginRequiredMixin, CreateView):
    model = Entrepot
    form_class = EntrepotForm
    template_name = 'dashboard/dashboard-add-space.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_edit_mode'] = False
        ctx['page_dashboard_title'] = 'Ajouter un espace'
        return ctx

    def dispatch(self, request, *args, **kwargs):
        if not user_has_owner_access(request.user):
            request.user.can_post_announcements = True
            request.user.save(update_fields=['can_post_announcements'])
            return redirect('core:dashboard_owner_mode_kyc_required')
        if not request.user.is_verified:
            return redirect('core:dashboard_owner_mode_kyc_required')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.user.is_verified:
            messages.error(
                self.request,
                'Votre compte doit être vérifié par l’équipe IbiHub avant publication.',
            )
            return HttpResponseRedirect(reverse('core:dashboard_add_space'))
        form.instance.proprietaire = self.request.user
        response = super().form_valid(form)
        n_gal = 0
        for f in self.request.FILES.getlist('images_galerie'):
            EntrepotImage.objects.create(
                entrepot=self.object,
                image=f,
                ordre=n_gal,
            )
            n_gal += 1
        msg = 'Annonce publiée avec succès.'
        if n_gal:
            msg = f'Annonce publiée avec {n_gal} photo(s) en galerie.'
        messages.success(self.request, msg)
        return response

    def get_success_url(self):
        return reverse('core:dashboard_spaces')


class EntrepotUpdateView(LoginRequiredMixin, UpdateView):
    model = Entrepot
    form_class = EntrepotForm
    template_name = 'dashboard/dashboard-add-space.html'

    def get_queryset(self):
        return Entrepot.objects.filter(proprietaire=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        if not user_has_owner_access(request.user):
            request.user.can_post_announcements = True
            request.user.save(update_fields=['can_post_announcements'])
            return redirect('core:dashboard_owner_mode_kyc_required')
        if not request.user.is_verified:
            return redirect('core:dashboard_owner_mode_kyc_required')
        try:
            obj = Entrepot.objects.get(
                pk=kwargs['pk'],
                proprietaire=request.user,
            )
        except Entrepot.DoesNotExist:
            raise Http404
        if entrepot_has_blocking_reservations(obj):
            messages.error(
                request,
                'Cet espace ne peut pas être modifié : une réservation est en attente '
                'ou une location confirmée est en cours.',
            )
            return redirect('core:dashboard_spaces')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_edit_mode'] = True
        ctx['page_dashboard_title'] = 'Modifier l’espace'
        return ctx

    def form_valid(self, form):
        if not self.request.user.is_verified:
            messages.error(
                self.request,
                'Votre compte doit être vérifié par l’équipe IbiHub.',
            )
            return HttpResponseRedirect(
                reverse('core:dashboard_edit_space', kwargs={'pk': self.object.pk})
            )
        response = super().form_valid(form)
        n0 = self.object.images.count()
        n_gal = 0
        for f in self.request.FILES.getlist('images_galerie'):
            EntrepotImage.objects.create(
                entrepot=self.object,
                image=f,
                ordre=n0 + n_gal,
            )
            n_gal += 1
        msg = 'Annonce mise à jour.'
        if n_gal:
            msg = f'Annonce mise à jour — {n_gal} nouvelle(s) photo(s) en galerie.'
        messages.success(self.request, msg)
        return response

    def get_success_url(self):
        return reverse('core:dashboard_spaces')


@login_required
def dashboard_reservations(request):
    _push_pending_referral_notifications(request)
    _push_owner_revenue_hint(request)
    user = request.user
    mode = get_dashboard_mode(request, user)
    today = timezone.now().date()
    ctx = {
        'today': today,
        'ibihub_commission_display': Reservation.get_commission_rate_display(),
        'is_owner_access': mode == 'OWNER',
    }

    if mode == 'OWNER' and user_has_owner_access(user):
        base = (
            Reservation.objects.filter(entrepot__proprietaire=user)
            .select_related('entrepot', 'client', 'entrepot__categorie')
            .order_by('-date_debut')
        )
        ctx['reservations_a_valider'] = list(
            base.filter(statut=Reservation.Statut.EN_ATTENTE)
        )
        ctx['reservations_historique'] = list(
            base.exclude(statut=Reservation.Statut.EN_ATTENTE)
        )
        ctx['litige_form'] = LitigeForm()
    else:
        reservations = list(
            Reservation.objects.filter(client=user)
            .select_related('entrepot', 'entrepot__categorie', 'etat_des_lieux')
            .order_by('-date_debut')
        )
        for r in reservations:
            if r.statut == Reservation.Statut.CONFIRME and r.qr_code_auth:
                r.qr_data_uri = qr_code_data_uri(r.qr_code_auth)
            else:
                r.qr_data_uri = None
        ctx['reservations'] = reservations

    return render(request, 'dashboard/dashboard-reservations.html', ctx)


@login_required
@require_POST
def reservation_confirm(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
    )
    if reservation.entrepot.proprietaire_id != request.user.id:
        raise PermissionDenied
    if reservation.statut != Reservation.Statut.EN_ATTENTE:
        messages.warning(request, 'Cette réservation ne peut plus être confirmée.')
        return redirect('core:dashboard_reservations')
    reservation.statut = Reservation.Statut.CONFIRME
    reservation.save()
    _send_reservation_confirmation_email(reservation, request=request)
    messages.success(
        request,
        f'Réservation #{reservation.pk} confirmée. Un QR code a été généré pour le client.',
    )
    return redirect('core:dashboard_reservations')


@login_required
@require_POST
def reservation_refuse(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
    )
    if reservation.entrepot.proprietaire_id != request.user.id:
        raise PermissionDenied
    if reservation.statut != Reservation.Statut.EN_ATTENTE:
        messages.warning(
            request,
            'Cette réservation ne peut plus être refusée.',
        )
        return redirect('core:dashboard_reservations')
    reservation.statut = Reservation.Statut.ANNULE
    reservation.save()
    messages.success(
        request,
        f'Réservation #{reservation.pk} refusée. Les dates sont à nouveau disponibles.',
    )
    return redirect('core:dashboard_reservations')


@require_POST
def demander_visite(request, pk):
    entrepot = get_object_or_404(
        Entrepot.objects.select_related('proprietaire'),
        pk=pk,
    )
    visit_date = (request.POST.get('visit_date') or '').strip()
    visit_note = (request.POST.get('visit_note') or '').strip()
    visitor_name = (request.POST.get('visit_name') or '').strip()
    visitor_email = (request.POST.get('visit_email') or '').strip()
    visitor_phone = (request.POST.get('visit_phone') or '').strip()

    if request.user.is_authenticated:
        visitor_name = visitor_name or request.user.get_full_name() or request.user.username
        visitor_email = visitor_email or request.user.email or request.user.username
        visitor_phone = visitor_phone or request.user.telephone

    if not visitor_name or not visitor_email or not visit_date:
        messages.error(
            request,
            'Merci de renseigner au moins votre nom, email et la date de visite souhaitée.',
        )
        return redirect('core:espace_detail', pk=entrepot.pk)

    recipient = getattr(
        settings,
        'CONTACT_RECIPIENT_EMAIL',
        settings.DEFAULT_FROM_EMAIL,
    )
    ctx_mail = {
        'entrepot': entrepot,
        'visit_date': visit_date,
        'visit_note': visit_note or '—',
        'visitor_name': visitor_name,
        'visitor_email': visitor_email,
        'visitor_phone': visitor_phone or '—',
    }
    html_body = render_to_string('emails/visit_request_notification.html', ctx_mail)
    text_body = render_to_string('emails/visit_request_notification.txt', ctx_mail)
    msg = EmailMultiAlternatives(
        subject=f"[IbiHub — Visite] {entrepot.titre} ({visit_date})",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        reply_to=[visitor_email],
    )
    msg.attach_alternative(html_body, 'text/html')
    msg.send(fail_silently=True)

    messages.success(request, 'Votre demande de visite a bien été envoyée.')
    return redirect('core:espace_detail', pk=entrepot.pk)


@login_required
@require_POST
def reserver_espace(request, pk):
    entrepot = get_object_or_404(
        Entrepot.objects.select_related('proprietaire'),
        pk=pk,
    )
    redirect_detail = HttpResponseRedirect(reverse('core:espace_detail', kwargs={'pk': entrepot.pk}))

    reservation_form_data = {
        'date_debut': (request.POST.get('date_debut') or '').strip(),
        'date_fin': (request.POST.get('date_fin') or '').strip(),
        'inventaire_depot': (request.POST.get('inventaire_depot') or '').strip(),
        'type_paiement': (request.POST.get('type_paiement') or '').strip(),
    }
    session_key = f'pending_reservation_form_{entrepot.pk}'

    if entrepot.proprietaire_id == request.user.id:
        messages.error(
            request,
            'Vous ne pouvez pas réserver votre propre espace.',
        )
        return redirect_detail

    if not entrepot.disponible:
        messages.error(
            request,
            'Cet espace n’est pas disponible à la réservation pour le moment.',
        )
        return redirect_detail

    if not entrepot.proprietaire.is_verified:
        messages.error(
            request,
            'Ce propriétaire n’a pas encore finalisé sa vérification : réservation impossible.',
        )
        return redirect_detail

    date_debut, date_fin = _parse_reservation_dates(request.POST)
    if date_debut is None or date_fin is None:
        request.session[session_key] = reservation_form_data
        messages.error(
            request,
            'Indiquez une date de début et une date de fin valides.',
        )
        return redirect_detail

    today = timezone.now().date()
    if date_debut < today:
        request.session[session_key] = reservation_form_data
        messages.error(
            request,
            'La date de début ne peut pas être dans le passé.',
        )
        return redirect_detail

    if date_fin < date_debut:
        request.session[session_key] = reservation_form_data
        messages.error(
            request,
            'La date de fin doit être égale ou postérieure à la date de début.',
        )
        return redirect_detail

    if booking_range_unavailable(entrepot, date_debut, date_fin):
        request.session[session_key] = reservation_form_data
        messages.error(
            request,
            'Ces dates ne sont pas disponibles (réservation existante ou période fermée).',
        )
        return redirect_detail

    inventaire = (request.POST.get('inventaire_depot') or '').strip()[:8000]
    type_paiement = request.POST.get('type_paiement') or Reservation.TypePaiement.UNIQUE
    if type_paiement not in {Reservation.TypePaiement.UNIQUE, Reservation.TypePaiement.MENSUEL}:
        type_paiement = Reservation.TypePaiement.UNIQUE

    reservation = Reservation(
        entrepot=entrepot,
        client=request.user,
        date_debut=date_debut,
        date_fin=date_fin,
        statut=Reservation.Statut.CONFIRME,
        inventaire_depot=inventaire,
        inventaire_photo=request.FILES.get('inventaire_photo'),
        type_paiement=type_paiement,
    )
    reservation.save()
    request.session.pop(session_key, None)
    _send_reservation_confirmation_email(reservation, request=request)

    return HttpResponseRedirect(
        f"{reverse('core:confirmation_reservation')}?reservation={reservation.pk}"
    )


@login_required
@require_POST
def reservation_quick_checkin(request):
    if not user_has_owner_access(request.user):
        raise PermissionDenied
    code = (request.POST.get('code_court') or '').strip().upper()
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        code_court=code,
        entrepot__proprietaire=request.user,
    )
    if reservation.statut != Reservation.Statut.CONFIRME:
        messages.warning(request, 'Cette réservation n’est pas confirmée.')
        return redirect('core:dashboard_reservations')
    if not reservation.checkin_at:
        reservation.checkin_at = timezone.now()
        reservation.save(update_fields=['checkin_at'])
    messages.success(request, f'Arrivée validée pour la réservation #{reservation.pk}.')
    return redirect('core:dashboard_reservations')


@login_required
@require_POST
def reservation_checkin_action(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
        client=request.user,
    )
    if reservation.statut != Reservation.Statut.CONFIRME:
        messages.warning(request, 'Réservation non confirmée.')
        return redirect('core:dashboard_reservations')
    reservation.checkin_at = timezone.now()
    reservation.save(update_fields=['checkin_at'])
    messages.success(request, 'Entrée enregistrée.')
    return redirect('core:dashboard_reservations')


@login_required
@require_POST
def reservation_checkout_action(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
        client=request.user,
    )
    if reservation.statut != Reservation.Statut.CONFIRME:
        messages.warning(request, 'Réservation non confirmée.')
        return redirect('core:dashboard_reservations')
    reservation.checkout_at = timezone.now()
    reservation.statut = Reservation.Statut.TERMINE
    reservation.save(update_fields=['checkout_at', 'statut'])
    messages.success(request, 'Sortie enregistrée.')
    return redirect('core:dashboard_reservations')


@login_required
@require_POST
def reservation_litige_create(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
        client=request.user,
    )
    form = LitigeForm(request.POST)
    if form.is_valid():
        litige = form.save(commit=False)
        litige.reservation = reservation
        litige.save()
        messages.success(request, 'Litige déclaré. Notre équipe analysera votre dossier.')
    else:
        messages.error(request, 'Merci de renseigner le motif et la description du litige.')
    return redirect('core:dashboard_reservations')


@login_required
def reservation_etat_des_lieux(request, pk):
    reservation = get_object_or_404(
        Reservation.objects.select_related('entrepot'),
        pk=pk,
    )
    if request.user.id not in {reservation.client_id, reservation.entrepot.proprietaire_id}:
        raise PermissionDenied
    etat, _ = EtatDesLieux.objects.get_or_create(reservation=reservation)
    if request.method == 'POST':
        form = EtatDesLieuxForm(request.POST, request.FILES, instance=etat)
        if form.is_valid():
            etat = form.save(commit=False)
            etat.date_validation = timezone.now()
            etat.save()
            messages.success(request, 'État des lieux mis à jour.')
            return redirect('core:dashboard_reservations')
    else:
        form = EtatDesLieuxForm(instance=etat)
    return render(
        request,
        'dashboard/dashboard-etat-des-lieux.html',
        {'form': form, 'reservation': reservation},
    )


@login_required
@require_POST
def espace_avis_create(request, pk):
    entrepot = get_object_or_404(Entrepot, pk=pk)
    redir = HttpResponseRedirect(reverse('core:espace_detail', kwargs={'pk': pk}))
    if request.user.pk == entrepot.proprietaire_id:
        messages.error(request, 'Vous ne pouvez pas noter votre propre espace.')
        return redir
    if EntrepotAvis.objects.filter(entrepot=entrepot, auteur=request.user).exists():
        messages.warning(request, 'Vous avez déjà publié un avis pour cet espace.')
        return redir
    form = EntrepotAvisForm(request.POST)
    if form.is_valid():
        avis = form.save(commit=False)
        avis.entrepot = entrepot
        avis.auteur = request.user
        avis.save()
        messages.success(request, 'Merci, votre avis a été publié.')
    else:
        messages.error(
            request,
            'Veuillez corriger le formulaire (note et commentaire requis).',
        )
    return redir


class EntrepotDetailView(DetailView):
    model = Entrepot
    template_name = 'public/espace-detail.html'
    context_object_name = 'entrepot'

    def get_queryset(self):
        qs = Entrepot.objects.select_related('categorie', 'proprietaire').prefetch_related(
            'images',
        )
        u = self.request.user
        if u.is_authenticated:
            return qs.filter(
                Q(proprietaire_id=u.pk)
                | Q(disponible=True, proprietaire__is_verified=True)
            ).distinct()
        return qs.filter(disponible=True, proprietaire__is_verified=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        e = self.object
        user = self.request.user
        is_owner_of_space = user.is_authenticated and user.pk == e.proprietaire_id
        ctx['booking_requires_login'] = not user.is_authenticated
        ctx['booking_blocked_own'] = is_owner_of_space
        ctx['can_submit_reservation'] = (
            user.is_authenticated
            and not is_owner_of_space
            and e.disponible
            and e.proprietaire.is_verified
        )
        slides = []
        for im in e.images.all():
            slides.append(im.image.url)
        if not slides and e.image_principale:
            slides.append(e.image_principale.url)
        ctx['gallery_slides'] = slides

        avis_base = EntrepotAvis.objects.filter(entrepot=e)
        ctx['avis_recent'] = list(
            avis_base.select_related('auteur').order_by('-created_at')[:5]
        )
        agg = avis_base.aggregate(avg=Avg('note'), n=Count('id'))
        ctx['avis_count'] = agg['n'] or 0
        ctx['avis_avg'] = (
            round(float(agg['avg']), 1) if agg['n'] and agg['avg'] is not None else None
        )
        can_post_avis = (
            user.is_authenticated
            and not is_owner_of_space
            and not avis_base.filter(auteur=user).exists()
        )
        ctx['can_post_avis'] = can_post_avis
        ctx['avis_form'] = EntrepotAvisForm() if can_post_avis else None
        ctx['availability_ranges_json'] = json.dumps(
            entrepot_blocked_date_ranges_iso(e),
            ensure_ascii=False,
        )
        ctx['availability_blocked_days_json'] = json.dumps(
            entrepot_blocked_date_strings_iso(e),
            ensure_ascii=False,
        )
        ctx['entrepot_caution_requise'] = e.caution_requise
        ctx['entrepot_caution_fixe'] = e.montant_caution_fixe
        pending_form = self.request.session.pop(f'pending_reservation_form_{e.pk}', None)
        if not isinstance(pending_form, dict):
            pending_form = {}
        ctx['reservation_form_initial'] = pending_form
        ctx['share_absolute_url'] = self.request.build_absolute_uri(
            reverse('core:espace_detail', kwargs={'pk': e.pk})
        )
        ctx['is_favori'] = (
            user.is_authenticated
            and Favori.objects.filter(user=user, entrepot=e).exists()
        )
        return ctx


class DashboardSettingsView(LoginRequiredMixin, UpdateView):
    model = UserCustom
    form_class = UserProfileForm
    template_name = 'dashboard/dashboard-settings.html'
    success_url = reverse_lazy('core:dashboard_settings')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        _push_pending_referral_notifications(self.request)
        password_form = kwargs.pop('password_form', None)
        active_settings_tab = kwargs.pop('active_settings_tab', None)
        ctx = super().get_context_data(**kwargs)
        ctx['password_form'] = (
            password_form
            if password_form is not None
            else PasswordChangeForm(self.request.user)
        )
        pf = ctx['password_form']
        pf.fields['old_password'].label = 'Mot de passe actuel'
        pf.fields['new_password1'].label = 'Nouveau mot de passe'
        pf.fields['new_password2'].label = 'Confirmer le nouveau mot de passe'
        tab_from_query = (self.request.GET.get('tab') or '').strip().lower()
        ctx['active_settings_tab'] = active_settings_tab or tab_from_query or 'profile'
        history_qs = Reservation.objects.filter(
            client=self.request.user,
            statut=Reservation.Statut.TERMINE,
        ).select_related('entrepot').order_by('-date_fin')[:100]
        ctx['billing_history'] = history_qs
        ctx['referral_balance'] = self.request.user.solde_parrainage
        ctx['referral_children_count'] = self.request.user.filleuls.count()
        ctx['referral_history'] = ParrainageGain.objects.filter(
            parrain=self.request.user
        ).select_related('filleul', 'reservation').order_by('-created_at')[:50]
        return ctx

    def post(self, request, *args, **kwargs):
        if request.POST.get('form_type') == 'password':
            self.object = self.get_object()
            pf = PasswordChangeForm(request.user, request.POST)
            if pf.is_valid():
                pf.save()
                update_session_auth_hash(request, pf.user)
                messages.success(request, 'Votre mot de passe a été mis à jour.')
                return HttpResponseRedirect(self.success_url)
            return self.render_to_response(
                self.get_context_data(
                    password_form=pf,
                    active_settings_tab='password',
                )
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Vos informations ont été enregistrées.')
        return super().form_valid(form)
