import base64
import io
import json
import random
from datetime import datetime
from decimal import Decimal, InvalidOperation

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from .forms import (
    ContactForm,
    EntrepotAvisForm,
    EntrepotForm,
    IbiHubAuthenticationForm,
    UserProfileForm,
    UserRegistrationForm,
)
from .models import (
    CategorieStorage,
    Entrepot,
    EntrepotAvis,
    EntrepotImage,
    Reservation,
    UserCustom,
)
from .utils_reservation import entrepot_blocked_date_ranges_iso, entrepot_has_blocking_reservations


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
    # 6 espaces publiés, tirés au hasard à chaque affichage
    entrepot_qs = Entrepot.objects.select_related('categorie', 'proprietaire')
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
    entrepots = Entrepot.objects.select_related('categorie', 'proprietaire').order_by(
        '-created_at'
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

    return render(
        request,
        'public/espaces.html',
        {
            'entrepots': entrepots,
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
                messages.success(
                    request,
                    'Merci ! Votre message a bien été envoyé. Nous vous répondons sous 2 jours ouvrés.',
                )
                return redirect('core:contact')
    else:
        form = ContactForm()
    return render(request, 'public/contact.html', {'form': form})


def reclamation(request):
    return render(request, 'public/reclamation.html')


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
        messages.success(self.request, 'Bienvenue sur IbiHub.')
        return HttpResponseRedirect(self.get_success_url())

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


def _reservation_dates_overlap_entrepot(entrepot, date_debut, date_fin) -> bool:
    """True si une réservation en attente ou confirmée chevauche [date_debut, date_fin]."""
    return (
        Reservation.objects.filter(
            entrepot=entrepot,
            statut__in=[
                Reservation.Statut.EN_ATTENTE,
                Reservation.Statut.CONFIRME,
            ],
            date_debut__lte=date_fin,
            date_fin__gte=date_debut,
        ).exists()
    )


@login_required
def mon_dashboard(request):
    user = request.user
    ctx = {
        'is_owner': user.role == 'OWNER',
    }
    if user.role == 'OWNER':
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
    else:
        today = timezone.now().date()
        merchant_list = list(
            Reservation.objects.filter(
                client=user,
                statut__in=[
                    Reservation.Statut.EN_ATTENTE,
                    Reservation.Statut.CONFIRME,
                ],
                date_fin__gte=today,
            )
            .select_related('entrepot', 'entrepot__categorie')
            .order_by('-date_debut')[:12]
        )
        for r in merchant_list:
            if r.statut == Reservation.Statut.CONFIRME and r.qr_code_auth:
                r.qr_data_uri = qr_code_data_uri(r.qr_code_auth)
            else:
                r.qr_data_uri = None
        ctx['merchant_reservations'] = merchant_list
    return render(request, 'dashboard/dashboard_user.html', ctx)


@login_required
def dashboard_spaces(request):
    if request.user.role != 'OWNER':
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


class EntrepotCreateView(LoginRequiredMixin, CreateView):
    model = Entrepot
    form_class = EntrepotForm
    template_name = 'dashboard/dashboard-add-space.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_edit_mode'] = False
        ctx['page_dashboard_title'] = 'Ajouter un espace'
        return ctx

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'OWNER':
            messages.error(
                request,
                'Seuls les propriétaires peuvent publier une annonce.',
            )
            return redirect('core:mon_dashboard')
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
        if request.user.role != 'OWNER':
            messages.error(
                request,
                'Seuls les propriétaires peuvent modifier une annonce.',
            )
            return redirect('core:mon_dashboard')
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
    user = request.user
    today = timezone.now().date()
    ctx = {'today': today}

    if user.role == 'OWNER':
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
    else:
        reservations = list(
            Reservation.objects.filter(client=user)
            .select_related('entrepot', 'entrepot__categorie')
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


@login_required
@require_POST
def reserver_espace(request, pk):
    entrepot = get_object_or_404(
        Entrepot.objects.select_related('proprietaire'),
        pk=pk,
    )
    redirect_detail = HttpResponseRedirect(
        reverse('core:espace_detail', kwargs={'pk': entrepot.pk})
    )

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

    date_debut, date_fin = _parse_reservation_dates(request.POST)
    if date_debut is None or date_fin is None:
        messages.error(
            request,
            'Indiquez une date de début et une date de fin valides.',
        )
        return redirect_detail

    today = timezone.now().date()
    if date_debut < today:
        messages.error(
            request,
            'La date de début ne peut pas être dans le passé.',
        )
        return redirect_detail

    if date_fin < date_debut:
        messages.error(
            request,
            'La date de fin doit être égale ou postérieure à la date de début.',
        )
        return redirect_detail

    if _reservation_dates_overlap_entrepot(entrepot, date_debut, date_fin):
        messages.error(
            request,
            'Ces dates se chevauchent avec une réservation déjà en cours ou en attente.',
        )
        return redirect_detail

    reservation = Reservation(
        entrepot=entrepot,
        client=request.user,
        date_debut=date_debut,
        date_fin=date_fin,
        statut=Reservation.Statut.EN_ATTENTE,
    )
    reservation.save()

    return HttpResponseRedirect(
        f"{reverse('core:confirmation_reservation')}?reservation={reservation.pk}"
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
    queryset = Entrepot.objects.select_related('categorie', 'proprietaire').prefetch_related(
        'images',
    )

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
        return ctx


class DashboardSettingsView(LoginRequiredMixin, UpdateView):
    model = UserCustom
    form_class = UserProfileForm
    template_name = 'dashboard/dashboard-settings.html'
    success_url = reverse_lazy('core:dashboard_settings')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        password_form = kwargs.pop('password_form', None)
        active_settings_tab = kwargs.pop('active_settings_tab', None)
        ctx = super().get_context_data(**kwargs)
        ctx['password_form'] = (
            password_form
            if password_form is not None
            else PasswordChangeForm(self.request.user)
        )
        ctx['active_settings_tab'] = active_settings_tab or 'profile'
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
