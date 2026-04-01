from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from . import views
from .forms import IbiHubPasswordResetForm, IbiHubSetPasswordForm

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('espaces/', views.liste_espaces, name='liste_espaces'),
    path(
        'espaces/<int:pk>/avis/',
        views.espace_avis_create,
        name='espace_avis_create',
    ),
    path(
        'espaces/<int:pk>/',
        views.EntrepotDetailView.as_view(),
        name='espace_detail',
    ),
    path(
        'espaces/<int:pk>/favori/',
        views.toggle_favori,
        name='toggle_favori',
    ),
    path(
        'espaces/<int:pk>/reserver/',
        views.reserver_espace,
        name='reserver_espace',
    ),
    path(
        'espaces/<int:pk>/demander-visite/',
        views.demander_visite,
        name='demander_visite',
    ),
    path(
        'confirmation-reservation/',
        views.confirmation_reservation,
        name='confirmation_reservation',
    ),
    path('a-propos/', views.a_propos, name='a_propos'),
    path(
        'opportunites-immobilieres/',
        views.opportunites_immobilieres,
        name='opportunites_immobilieres',
    ),
    path('contact/', views.contact, name='contact'),
    path(
        'contact/confirmation/',
        views.confirmation_contact,
        name='confirmation_contact',
    ),
    path(
        'auth/mot-de-passe-oublie/',
        auth_views.PasswordResetView.as_view(
            template_name='public/auth/password_reset_form.html',
            form_class=IbiHubPasswordResetForm,
            email_template_name='emails/password_reset_email.txt',
            subject_template_name='emails/password_reset_subject.txt',
            success_url=reverse_lazy('core:password_reset_done'),
            extra_context={'title': 'Mot de passe oublié'},
        ),
        name='password_reset',
    ),
    path(
        'auth/mot-de-passe-oublie/envoye/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='public/auth/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'auth/reinitialiser/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='public/auth/password_reset_confirm.html',
            form_class=IbiHubSetPasswordForm,
            success_url=reverse_lazy('core:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'auth/mot-de-passe-modifie/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='public/auth/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path('legal/confidentialite/', views.politique_confidentialite, name='legal_confidentialite'),
    path('legal/conditions/', views.conditions_utilisation, name='legal_cgu'),
    path(
        'legal/securite-espaces/',
        views.politique_securite_espaces,
        name='legal_securite_espaces',
    ),
    path('connexion/', views.IbiHubLoginView.as_view(), name='sign_in'),
    path('inscription/', views.SignUpView.as_view(), name='sign_up'),
    path(
        'deconnexion/',
        LogoutView.as_view(),
        name='logout',
    ),
    path('reclamation/', views.reclamation, name='reclamation'),
    path(
        'reclamation/confirmation/',
        views.confirmation_reclamation,
        name='confirmation_reclamation',
    ),
    path('dashboard/', views.mon_dashboard, name='mon_dashboard'),
    path(
        'dashboard/devenir-proprietaire/',
        views.activate_owner_mode,
        name='activate_owner_mode',
    ),
    path('dashboard/switch-mode/', views.dashboard_switch_mode, name='dashboard_switch_mode'),
    path(
        'dashboard/mode-proprietaire-kyc/',
        views.dashboard_owner_mode_kyc_required,
        name='dashboard_owner_mode_kyc_required',
    ),
    path('dashboard/favoris/', views.dashboard_favorites, name='dashboard_favorites'),
    path('dashboard/facturation/', views.dashboard_billing, name='dashboard_billing'),
    path('dashboard/parrainage/', views.dashboard_referral, name='dashboard_referral'),
    path(
        'dashboard/disponibilites/',
        views.dashboard_disponibilites,
        name='dashboard_disponibilites',
    ),
    path(
        'dashboard/disponibilites/<int:pk>/supprimer/',
        views.dashboard_disponibilites_delete,
        name='dashboard_disponibilites_delete',
    ),
    path(
        'dashboard/verification-compte/',
        views.dashboard_owner_kyc,
        name='dashboard_owner_kyc',
    ),
    path(
        'dashboard/admin/commissions/',
        views.dashboard_admin_analytics,
        name='dashboard_admin_analytics',
    ),
    path(
        'dashboard/admin/cautions/<int:pk>/liberer/',
        views.reservation_liberer_caution,
        name='reservation_liberer_caution',
    ),
    path(
        'dashboard/reservations/<int:pk>/contrat.pdf',
        views.reservation_contrat_download,
        name='reservation_contrat_pdf',
    ),
    path(
        'dashboard/reservations/<int:pk>/ticket.pdf',
        views.reservation_ticket_download,
        name='reservation_ticket_pdf',
    ),
    path('dashboard/espaces/', views.dashboard_spaces, name='dashboard_spaces'),
    path(
        'dashboard/espaces/ajouter/',
        views.EntrepotCreateView.as_view(),
        name='dashboard_add_space',
    ),
    path(
        'dashboard/espaces/<int:pk>/modifier/',
        views.EntrepotUpdateView.as_view(),
        name='dashboard_edit_space',
    ),
    path(
        'dashboard/espaces/<int:pk>/boost/',
        views.entrepot_boost_activate,
        name='dashboard_boost_space',
    ),
    path(
        'dashboard/reservations/',
        views.dashboard_reservations,
        name='dashboard_reservations',
    ),
    path(
        'dashboard/reservations/<int:pk>/confirmer/',
        views.reservation_confirm,
        name='confirmer_reservation',
    ),
    path(
        'dashboard/reservations/<int:pk>/refuser/',
        views.reservation_refuse,
        name='refuser_reservation',
    ),
    path(
        'dashboard/reservations/arrivee-code/',
        views.reservation_quick_checkin,
        name='reservation_quick_checkin',
    ),
    path(
        'dashboard/reservations/<int:pk>/checkin/',
        views.reservation_checkin_action,
        name='reservation_checkin_action',
    ),
    path(
        'dashboard/reservations/<int:pk>/checkout/',
        views.reservation_checkout_action,
        name='reservation_checkout_action',
    ),
    path(
        'dashboard/reservations/<int:pk>/litige/',
        views.reservation_litige_create,
        name='reservation_litige_create',
    ),
    path(
        'dashboard/reservations/<int:pk>/etat-des-lieux/',
        views.reservation_etat_des_lieux,
        name='reservation_etat_des_lieux',
    ),
    path(
        'dashboard/parametres/',
        views.DashboardSettingsView.as_view(),
        name='dashboard_settings',
    ),
]
