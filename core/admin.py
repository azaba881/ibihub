from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    CategorieStorage,
    Entrepot,
    EntrepotAvis,
    EntrepotIndisponibilite,
    EtatDesLieux,
    EntrepotImage,
    EntrepotPeriodeBloquee,
    Favori,
    Litige,
    ParrainageGain,
    Reservation,
    UserCustom,
)


@admin.register(UserCustom)
class UserCustomAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Ibihub',
            {
                'fields': (
                    'role',
                    'can_post_announcements',
                    'telephone',
                    'photo_profil',
                    'is_verified',
                    'code_parrainage',
                    'parrain',
                    'type_piece',
                    'piece_identite',
                )
            },
        ),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'telephone'),
        }),
    )
    list_display = (*BaseUserAdmin.list_display, 'role', 'telephone', 'is_verified')
    list_filter = (*BaseUserAdmin.list_filter, 'role')


@admin.register(CategorieStorage)
class CategorieStorageAdmin(admin.ModelAdmin):
    list_display = ('nom', 'icone', 'image')
    search_fields = ('nom',)
    fields = ('nom', 'icone', 'image')


class EntrepotImageInline(admin.TabularInline):
    model = EntrepotImage
    extra = 1
    fields = ('image', 'ordre')


class EntrepotPeriodeBloqueeInline(admin.TabularInline):
    model = EntrepotPeriodeBloquee
    extra = 0
    fields = ('date_debut', 'date_fin', 'motif')


class EntrepotIndisponibiliteInline(admin.TabularInline):
    model = EntrepotIndisponibilite
    extra = 0
    fields = ('date_debut', 'date_fin', 'raison')


@admin.register(EntrepotAvis)
class EntrepotAvisAdmin(admin.ModelAdmin):
    list_display = ('entrepot', 'auteur', 'note', 'created_at')
    list_filter = ('note', 'created_at')
    search_fields = ('commentaire', 'entrepot__titre', 'auteur__username')
    raw_id_fields = ('entrepot', 'auteur')


@admin.register(EntrepotImage)
class EntrepotImageAdmin(admin.ModelAdmin):
    list_display = ('entrepot', 'ordre', 'image')
    list_filter = ('entrepot__categorie',)
    search_fields = ('entrepot__titre',)


@admin.register(Entrepot)
class EntrepotAdmin(admin.ModelAdmin):
    inlines = (EntrepotPeriodeBloqueeInline, EntrepotIndisponibiliteInline, EntrepotImageInline)
    list_display = (
        'titre',
        'proprietaire',
        'categorie',
        'ville',
        'prix_par_jour',
        'surface_m2',
        'caution_requise',
        'montant_caution_fixe',
        'is_boosted',
        'boost_expires_at',
        'disponible',
        'created_at',
    )
    list_filter = ('ville', 'disponible', 'categorie')
    search_fields = ('titre', 'adresse', 'proprietaire__username')
    raw_id_fields = ('proprietaire',)
    readonly_fields = ('created_at',)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'entrepot',
        'client',
        'date_debut',
        'date_fin',
        'montant_total',
        'frais_assurance',
        'montant_caution',
        'caution_rendue',
        'code_court',
        'type_paiement',
        'prochaine_echeance',
        'revenu_net_proprietaire',
        'statut',
        'qr_code_auth',
    )
    list_filter = ('statut', 'date_debut')
    search_fields = ('entrepot__titre', 'client__username', 'qr_code_auth')
    raw_id_fields = ('entrepot', 'client')
    readonly_fields = (
        'montant_total',
        'frais_assurance',
        'montant_caution',
        'caution_rendue',
        'revenu_net_proprietaire',
        'qr_code_auth',
        'code_court',
        'contrat_pdf',
        'ticket_pdf',
    )


@admin.register(EntrepotIndisponibilite)
class EntrepotIndisponibiliteAdmin(admin.ModelAdmin):
    list_display = ('entrepot', 'date_debut', 'date_fin', 'raison', 'created_at')
    list_filter = ('date_debut',)
    search_fields = ('entrepot__titre', 'raison')


@admin.register(ParrainageGain)
class ParrainageGainAdmin(admin.ModelAdmin):
    list_display = ('parrain', 'filleul', 'reservation', 'montant', 'created_at', 'notified')
    list_filter = ('created_at', 'notified')
    search_fields = ('parrain__username', 'filleul__username')


@admin.register(Favori)
class FavoriAdmin(admin.ModelAdmin):
    list_display = ('user', 'entrepot', 'created_at')
    search_fields = ('user__username', 'entrepot__titre')


@admin.register(EtatDesLieux)
class EtatDesLieuxAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'date_validation')
    search_fields = ('reservation__id', 'reservation__client__username')
    raw_id_fields = ('reservation',)


@admin.register(Litige)
class LitigeAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'motif', 'statut', 'created_at')
    list_filter = ('statut', 'created_at')
    search_fields = ('motif', 'description', 'reservation__id')
    raw_id_fields = ('reservation',)
