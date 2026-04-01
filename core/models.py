import uuid
import random
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


def validate_telephone_e164(value: str) -> None:
    """Numéro international E.164 (ex. +22990123456)."""
    if value is None or not str(value).strip():
        return
    s = str(value).strip()
    if not s.startswith('+'):
        raise ValidationError(
            'Le numéro doit être au format international E.164 (commence par +).'
        )
    digits = ''.join(c for c in s[1:] if c.isdigit())
    if len(digits) < 8:
        raise ValidationError('Le numéro est trop court.')
    if len(digits) > 15:
        raise ValidationError('Le numéro est trop long.')


# Compatibilité : les migrations historiques référencent ce nom
validate_telephone_benin_local = validate_telephone_e164


class UserCustom(AbstractUser):
    ROLE_CHOICES = [
        ('OWNER', 'Propriétaire'),
        ('MERCHANT', 'Commerçant'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='MERCHANT',
    )
    can_post_announcements = models.BooleanField(
        default=False,
        help_text='Active les fonctionnalités propriétaire sans changer de compte.',
    )
    telephone = models.CharField(
        max_length=24,
        blank=True,
        validators=[validate_telephone_e164],
        help_text='Format international E.164 (ex. +22990123456).',
    )
    photo_profil = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True,
    )
    is_verified = models.BooleanField(
        default=False,
        help_text='Compte vérifié par l’équipe (obligatoire pour publier une annonce).',
    )
    class TypePiece(models.TextChoices):
        CIP = 'CIP', 'CIP'
        CNI = 'CNI', 'CNI'
        PASSEPORT = 'PASSEPORT', 'Passeport'

    type_piece = models.CharField(
        max_length=16,
        choices=TypePiece.choices,
        blank=True,
        help_text='Type de pièce d’identité transmise pour vérification.',
    )
    piece_identite = models.ImageField(
        upload_to='kyc/',
        blank=True,
        null=True,
        help_text='Scan ou photo de la pièce (traitement par l’équipe IbiHub).',
    )
    code_parrainage = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
        null=True,
        help_text='Code unique de parrainage partagé à l’inscription.',
    )
    parrain = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='filleuls',
    )
    class ReseauMomo(models.TextChoices):
        MTN = 'MTN', 'MTN Mobile Money'
        MOOV = 'MOOV', 'Moov Money'

    reseau_momo = models.CharField(
        max_length=8,
        choices=ReseauMomo.choices,
        blank=True,
        help_text='Réseau Mobile Money par défaut.',
    )
    numero_momo = models.CharField(
        max_length=24,
        blank=True,
        validators=[validate_telephone_e164],
        help_text='Numéro Mobile Money (format international, ex. +229...).',
    )
    solde_parrainage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Cumul des gains de parrainage.',
    )

    def __str__(self) -> str:
        return self.get_username()

    @property
    def has_owner_access(self) -> bool:
        return self.role == 'OWNER' or self.can_post_announcements

    def _generate_referral_code(self) -> str:
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        for _ in range(100):
            candidate = ''.join(random.choice(alphabet) for _ in range(8))
            if not UserCustom.objects.filter(code_parrainage=candidate).exclude(pk=self.pk).exists():
                return candidate
        return uuid.uuid4().hex[:8].upper()

    def save(self, *args, **kwargs):
        if not self.code_parrainage:
            self.code_parrainage = self._generate_referral_code()
        super().save(*args, **kwargs)


class CategorieStorage(models.Model):
    nom = models.CharField(max_length=120)
    icone = models.CharField(
        max_length=80,
        help_text='Classe Font Awesome (ex. fa-warehouse, fa-box), affichée si aucune image.',
    )
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        help_text='Image représentative (optionnelle ; prioritaire sur l’icône sur le site).',
    )

    class Meta:
        verbose_name = 'catégorie de stockage'
        verbose_name_plural = 'catégories de stockage'

    def __str__(self) -> str:
        return self.nom


class Entrepot(models.Model):
    class Ville(models.TextChoices):
        COTONOU = 'Cotonou', 'Cotonou'
        PORTO_NOVO = 'Porto-Novo', 'Porto-Novo'
        PARAKOU = 'Parakou', 'Parakou'
        BOHICON = 'Bohicon', 'Bohicon'
        ABOMEY_CALAVI = 'Abomey-Calavi', 'Abomey-Calavi'

    proprietaire = models.ForeignKey(
        UserCustom,
        on_delete=models.CASCADE,
        related_name='entrepots',
    )
    categorie = models.ForeignKey(
        CategorieStorage,
        on_delete=models.PROTECT,
        related_name='entrepots',
    )
    titre = models.CharField(max_length=200)
    description_detaillee = models.TextField()
    adresse = models.CharField(max_length=255)
    ville = models.CharField(
        max_length=32,
        choices=Ville.choices,
    )
    image_principale = models.ImageField(upload_to='entrepots/')
    prix_par_jour = models.DecimalField(max_digits=10, decimal_places=2)
    surface_m2 = models.PositiveIntegerField()
    equipements = models.JSONField(
        default=list,
        blank=True,
        help_text='Options : Gardiennage, Caméras, Électricité, Zone Frigo (liste JSON).',
    )
    caution_requise = models.BooleanField(
        default=False,
        help_text="Active l'exigence de caution pour les durées longues (>= 14 jours).",
    )
    montant_caution_fixe = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Montant fixe de caution si caution_requise est activé et durée >= 14 jours.',
    )
    is_boosted = models.BooleanField(
        default=False,
        help_text='Annonce mise en avant.',
    )
    boost_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fin de mise en avant.',
    )
    disponible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'entrepôt'
        verbose_name_plural = 'entrepôts'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.titre


    def clean(self) -> None:
        super().clean()
        if self.disponible and self.proprietaire_id:
            if not UserCustom.objects.filter(
                pk=self.proprietaire_id,
                is_verified=True,
            ).exists():
                raise ValidationError(
                    {
                        'disponible': (
                            'Impossible de laisser l’annonce en ligne : votre compte '
                            'doit d’abord être vérifié par IbiHub (pièce d’identité).'
                        )
                    }
                )


class EntrepotPeriodeBloquee(models.Model):
    """Périodes verrouillées par le propriétaire / admin (maintenance, usage perso…)."""

    entrepot = models.ForeignKey(
        Entrepot,
        on_delete=models.CASCADE,
        related_name='periodes_bloquees',
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    motif = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['date_debut']
        verbose_name = 'période bloquée'
        verbose_name_plural = 'périodes bloquées'

    def __str__(self) -> str:
        return f'{self.entrepot.titre} — {self.date_debut} → {self.date_fin}'


class EntrepotIndisponibilite(models.Model):
    """Indisponibilité posée explicitement par le propriétaire."""

    entrepot = models.ForeignKey(
        Entrepot,
        on_delete=models.CASCADE,
        related_name='indisponibilites',
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    raison = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_debut']
        verbose_name = 'indisponibilité entrepôt'
        verbose_name_plural = 'indisponibilités entrepôt'

    def __str__(self) -> str:
        return f'{self.entrepot.titre} — indisponible du {self.date_debut} au {self.date_fin}'


class EntrepotImage(models.Model):
    """Photos additionnelles pour la fiche entrepôt (galerie)."""

    entrepot = models.ForeignKey(
        Entrepot,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image = models.ImageField(upload_to='entrepots/galerie/')
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'pk']
        verbose_name = 'image entrepôt'
        verbose_name_plural = 'images entrepôt'

    def __str__(self) -> str:
        return f'{self.entrepot.titre} — image {self.pk}'


class EntrepotAvis(models.Model):
    """Avis utilisateur sur une annonce (un avis par compte et par espace)."""

    entrepot = models.ForeignKey(
        Entrepot,
        on_delete=models.CASCADE,
        related_name='avis',
    )
    auteur = models.ForeignKey(
        UserCustom,
        on_delete=models.CASCADE,
        related_name='avis_espaces',
    )
    note = models.PositiveSmallIntegerField()
    commentaire = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'avis espace'
        verbose_name_plural = 'avis espaces'
        constraints = [
            models.UniqueConstraint(
                fields=('entrepot', 'auteur'),
                name='unique_entrepot_avis_par_auteur',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.entrepot.titre} — {self.auteur} ({self.note}/5)'


class Reservation(models.Model):
    class TypePaiement(models.TextChoices):
        UNIQUE = 'UNIQUE', 'Paiement unique'
        MENSUEL = 'MENSUEL', 'Paiement mensuel'

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        CONFIRME = 'CONFIRME', 'Confirmé'
        TERMINE = 'TERMINE', 'Terminé'
        ANNULE = 'ANNULE', 'Annulé'

    entrepot = models.ForeignKey(
        Entrepot,
        on_delete=models.CASCADE,
        related_name='reservations',
    )
    client = models.ForeignKey(
        UserCustom,
        on_delete=models.CASCADE,
        related_name='reservations_client',
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    frais_assurance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    revenu_net_proprietaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text='Net propriétaire après commission (recalculé à chaque enregistrement).',
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
    )
    qr_code_auth = models.SlugField(
        max_length=40,
        unique=True,
        blank=True,
        null=True,
        help_text='Identifiant unique pour authentification QR (généré à la confirmation).',
    )
    inventaire_depot = models.TextField(
        blank=True,
        help_text='Liste des marchandises déclarée par le locataire.',
    )
    montant_caution = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        editable=False,
        help_text='Caution : montant fixe de l’entrepôt ou pourcentage du loyer (settings).',
    )
    contrat_pdf = models.FileField(
        upload_to='reservations/contrats/',
        blank=True,
        null=True,
        help_text='Contrat de bail généré à la confirmation.',
    )
    ticket_pdf = models.FileField(
        upload_to='reservations/tickets/',
        blank=True,
        null=True,
        help_text='Version ticket simplifiée.',
    )
    code_court = models.CharField(
        max_length=7,
        unique=True,
        blank=True,
        null=True,
        help_text='Code d’accès court (ex. ABC-123).',
    )
    inventaire_photo = models.ImageField(
        upload_to='reservations/inventaires/',
        blank=True,
        null=True,
        help_text='Photo des marchandises déposées.',
    )
    type_paiement = models.CharField(
        max_length=12,
        choices=TypePaiement.choices,
        default=TypePaiement.UNIQUE,
    )
    prochaine_echeance = models.DateField(
        null=True,
        blank=True,
        help_text='Date de prochaine échéance pour paiement mensuel.',
    )
    checkin_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Horodatage de dépôt.',
    )
    checkout_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Horodatage de retrait.',
    )
    caution_rendue = models.BooleanField(
        default=False,
        help_text='Indique si la caution a été restituée.',
    )
    gain_parrainage_verse = models.BooleanField(
        default=False,
        help_text='Empêche de verser plusieurs fois la récompense de parrainage.',
    )

    class Meta:
        verbose_name = 'réservation'
        verbose_name_plural = 'réservations'
        ordering = ['-date_debut']

    def __str__(self) -> str:
        return f'{self.entrepot} — {self.client} ({self.get_statut_display()})'

    def calcule_duree_jours(self) -> int:
        """Nombre de jours de location (inclusif : même jour = 1 jour)."""
        if not self.date_debut or not self.date_fin:
            return 0
        jours = (self.date_fin - self.date_debut).days + 1
        return max(1, jours)

    def _generate_unique_code_court(self) -> str:
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
        digits = '23456789'
        for _ in range(80):
            left = ''.join(random.choice(alphabet) for _ in range(3))
            right = ''.join(random.choice(digits) for _ in range(3))
            code = f'{left}-{right}'
            if not Reservation.objects.filter(code_court=code).exclude(pk=self.pk).exists():
                return code
        return f'{uuid.uuid4().hex[:3].upper()}-{uuid.uuid4().hex[:3].upper()}'

    def calculer_caution(self) -> Decimal:
        """Caution appliquée uniquement si requise et durée >= 14 jours."""
        jours = self.calcule_duree_jours()
        if self.entrepot.caution_requise and jours >= 14:
            return Decimal(str(self.entrepot.montant_caution_fixe)).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @staticmethod
    def _format_commission_rate_display(rate) -> str:
        r = Decimal(str(rate))
        pct = (r * Decimal('100')).quantize(Decimal('0.01'))
        if pct % 1 == 0:
            return f'{int(pct)}%'
        return f'{pct.normalize()}%'

    @classmethod
    def get_commission_rate_display(cls) -> str:
        """Libellé du taux configuré (ex. « 5% », « 10% ») pour en-têtes de tableau, e-mails, etc."""
        return cls._format_commission_rate_display(settings.IBIHUB_COMMISSION_RATE)

    @property
    def taux_commission_display(self) -> str:
        return self.get_commission_rate_display()

    def clean(self) -> None:
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({
                'date_fin': 'La date de fin doit être égale ou postérieure à la date de début.',
            })

    def save(self, *args, **kwargs) -> None:
        self.full_clean(
            exclude=[
                'qr_code_auth',
                'revenu_net_proprietaire',
                'montant_total',
                'frais_assurance',
                'montant_caution',
                'contrat_pdf',
                'ticket_pdf',
            ]
        )
        jours = self.calcule_duree_jours()
        prix = self.entrepot.prix_par_jour
        rate = Decimal(str(settings.IBIHUB_COMMISSION_RATE))
        self.montant_total = (Decimal(jours) * prix).quantize(Decimal('0.01'))
        self.frais_assurance = (self.montant_total * rate).quantize(Decimal('0.01'))
        self.revenu_net_proprietaire = (
            self.montant_total - self.frais_assurance
        ).quantize(Decimal('0.01'))
        self.montant_caution = self.calculer_caution()
        if jours > 30 and self.type_paiement == self.TypePaiement.UNIQUE:
            # Le front peut proposer MENSUEL; on conserve UNIQUE par défaut.
            pass
        if self.type_paiement == self.TypePaiement.MENSUEL and not self.prochaine_echeance:
            from datetime import timedelta

            self.prochaine_echeance = self.date_debut + timedelta(days=30)
        if not self.code_court:
            self.code_court = self._generate_unique_code_court()
        if self.revenu_net_proprietaire > self.montant_total:
            raise ValidationError(
                {
                    'revenu_net_proprietaire': (
                        'Le revenu net ne peut pas dépasser le montant total de la réservation.'
                    )
                }
            )
        if self.revenu_net_proprietaire < 0:
            raise ValidationError(
                {'revenu_net_proprietaire': 'Le revenu net ne peut pas être négatif.'}
            )
        if self.statut == self.Statut.CONFIRME:
            if not self.qr_code_auth:
                self.qr_code_auth = self._generate_unique_qr_slug()
        super().save(*args, **kwargs)

    def _generate_unique_qr_slug(self) -> str:
        for _ in range(50):
            candidate = uuid.uuid4().hex[:24]
            if not Reservation.objects.filter(qr_code_auth=candidate).exclude(
                pk=self.pk
            ).exists():
                return candidate
        return uuid.uuid4().hex


class EtatDesLieux(models.Model):
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='etat_des_lieux',
    )
    photo_entree_1 = models.ImageField(upload_to='etats_des_lieux/', blank=True, null=True)
    photo_entree_2 = models.ImageField(upload_to='etats_des_lieux/', blank=True, null=True)
    photo_sortie_1 = models.ImageField(upload_to='etats_des_lieux/', blank=True, null=True)
    photo_sortie_2 = models.ImageField(upload_to='etats_des_lieux/', blank=True, null=True)
    commentaire_proprietaire = models.TextField(blank=True)
    commentaire_commercant = models.TextField(blank=True)
    date_validation = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "état des lieux"
        verbose_name_plural = "états des lieux"

    def __str__(self) -> str:
        return f"État des lieux réservation #{self.reservation_id}"

    @property
    def sortie_complete(self) -> bool:
        return bool(self.photo_sortie_1 and self.photo_sortie_2)


class Litige(models.Model):
    class Statut(models.TextChoices):
        OUVERT = 'OUVERT', 'Ouvert'
        EN_COURS = 'EN_COURS', 'En cours'
        RESOLU = 'RESOLU', 'Résolu'

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='litiges',
    )
    motif = models.CharField(max_length=180)
    description = models.TextField()
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.OUVERT)
    decision_admin = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'litige'
        verbose_name_plural = 'litiges'
        ordering = ['-created_at']


class ParrainageGain(models.Model):
    parrain = models.ForeignKey(
        UserCustom,
        on_delete=models.CASCADE,
        related_name='gains_parrainage',
    )
    filleul = models.ForeignKey(
        UserCustom,
        on_delete=models.CASCADE,
        related_name='gains_generees',
    )
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='gain_parrainage',
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('500.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'gain de parrainage'
        verbose_name_plural = 'gains de parrainage'
        ordering = ['-created_at']


class Favori(models.Model):
    user = models.ForeignKey(
        UserCustom,
        on_delete=models.CASCADE,
        related_name='favoris',
    )
    entrepot = models.ForeignKey(
        Entrepot,
        on_delete=models.CASCADE,
        related_name='favoris',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'favori'
        verbose_name_plural = 'favoris'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'entrepot'),
                name='unique_favori_user_entrepot',
            ),
        ]
