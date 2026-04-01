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
        'espaces/<int:pk>/reserver/',
        views.reserver_espace,
        name='reserver_espace',
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
        'dashboard/parametres/',
        views.DashboardSettingsView.as_view(),
        name='dashboard_settings',
    ),
]
