from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    CategorieStorage,
    Entrepot,
    EntrepotAvis,
    EntrepotImage,
    EntrepotPeriodeBloquee,
    Reservation,
    UserCustom,
)


@admin.register(UserCustom)
class UserCustomAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Ibihub', {'fields': ('role', 'telephone', 'photo_profil', 'is_verified')}),
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
    inlines = (EntrepotPeriodeBloqueeInline, EntrepotImageInline)
    list_display = (
        'titre',
        'proprietaire',
        'categorie',
        'ville',
        'prix_par_jour',
        'surface_m2',
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
        'statut',
        'qr_code_auth',
    )
    list_filter = ('statut', 'date_debut')
    search_fields = ('entrepot__titre', 'client__username', 'qr_code_auth')
    raw_id_fields = ('entrepot', 'client')
    readonly_fields = ('montant_total', 'frais_assurance', 'qr_code_auth')
