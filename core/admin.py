from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import (
    Article,
    ArticleCategorie,
    CategorieStorage,
    Entrepot,
    EntrepotAvis,
    EntrepotIndisponibilite,
    EtatDesLieux,
    EntrepotImage,
    EntrepotPeriodeBloquee,
    Favori,
    Litige,
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


class SuperuserBlogMixin:
    """Réservé aux super-utilisateurs (rédaction des articles vitrine)."""

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser


@admin.register(ArticleCategorie)
class ArticleCategorieAdmin(SuperuserBlogMixin, admin.ModelAdmin):
    list_display = ('nom', 'slug')
    prepopulated_fields = {'slug': ('nom',)}
    search_fields = ('nom', 'slug')


@admin.register(Article)
class ArticleAdmin(SuperuserBlogMixin, admin.ModelAdmin):
    list_display = ('titre', 'categorie', 'is_publie', 'published_at', 'auteur', 'updated_at')
    list_filter = ('is_publie', 'categorie', 'published_at')
    search_fields = ('titre', 'slug', 'resume', 'contenu')
    prepopulated_fields = {'slug': ('titre',)}
    raw_id_fields = ('auteur',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('titre', 'slug', 'categorie', 'resume', 'contenu', 'image_couverture')}),
        ('Publication', {'fields': ('is_publie', 'published_at', 'auteur')}),
        ('Métadonnées', {'fields': ('created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if obj.is_publie and not obj.published_at:
            obj.published_at = timezone.now()
        if not obj.auteur_id and request.user.is_authenticated:
            obj.auteur = request.user
        super().save_model(request, obj, form, change)


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
