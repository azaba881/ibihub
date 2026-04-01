import uuid
from decimal import Decimal

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

    def __str__(self) -> str:
        return self.get_username()


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
    disponible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'entrepôt'
        verbose_name_plural = 'entrepôts'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.titre


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
    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        CONFIRME = 'CONFIRME', 'Confirmé'
        TERMINE = 'TERMINE', 'Terminé'
        ANNULE = 'ANNULE', 'Annulé'

    TAUX_ASSURANCE = Decimal('0.05')

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

    @property
    def revenu_net_proprietaire(self) -> Decimal:
        """Montant encaissable par le propriétaire après déduction des frais d’assurance (5 %)."""
        return (self.montant_total - self.frais_assurance).quantize(Decimal('0.01'))

    def clean(self) -> None:
        super().clean()
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({
                'date_fin': 'La date de fin doit être égale ou postérieure à la date de début.',
            })

    def save(self, *args, **kwargs) -> None:
        self.full_clean(exclude=['qr_code_auth'])
        jours = self.calcule_duree_jours()
        prix = self.entrepot.prix_par_jour
        self.montant_total = (Decimal(jours) * prix).quantize(Decimal('0.01'))
        self.frais_assurance = (self.montant_total * self.TAUX_ASSURANCE).quantize(
            Decimal('0.01')
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
