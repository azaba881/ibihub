import re

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import (
    Entrepot,
    EntrepotAvis,
    EntrepotIndisponibilite,
    EtatDesLieux,
    Litige,
    UserCustom,
)


class IbiHubPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update(
            {
                'class': 'ibihub-auth-input',
                'autocomplete': 'email',
                'placeholder': 'vous@exemple.com',
            }
        )


class IbiHubSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('new_password1', 'new_password2'):
            self.fields[name].widget.attrs.setdefault('class', 'ibihub-auth-input')


class IbiHubAuthenticationForm(AuthenticationForm):
    """Connexion avec e-mail (username) ou téléphone — voir EmailOrPhoneBackend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email ou numéro de téléphone'
        self.fields['username'].widget.attrs.update(
            {
                'placeholder': 'Email ou numéro de téléphone',
                'autocomplete': 'username',
                'class': 'ibihub-auth-input',
                'inputmode': 'text',
            }
        )


class UserRegistrationForm(UserCreationForm):
    """Inscription : le champ « username » sert d’email / identifiant de connexion."""

    class Meta:
        model = UserCustom
        fields = ('username', 'telephone', 'role', 'password1', 'password2')
        labels = {
            'username': 'Email',
            'telephone': 'Téléphone',
            'role': 'Je suis',
            'password1': 'Mot de passe',
            'password2': 'Confirmation du mot de passe',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.EmailInput(
            attrs={'placeholder': 'vous@exemple.com', 'autocomplete': 'email'}
        )
        self.fields['username'].help_text = 'Sert d’identifiant pour vous connecter.'
        self.fields['telephone'].required = False
        self.fields['telephone'].widget = forms.TextInput(
            attrs={
                'type': 'tel',
                'autocomplete': 'tel',
                'class': 'ibihub-auth-input ibihub-intl-phone',
                'id': 'id_telephone',
            }
        )
        self.fields['telephone'].help_text = (
            'Indicatif et numéro au format international (E.164 enregistré à la validation).'
        )
        self.fields['role'].widget = forms.HiddenInput()
        self.fields['role'].initial = 'MERCHANT'
        self.fields['parrainage_code_input'] = forms.CharField(
            required=False,
            max_length=20,
            label='Code de parrainage (optionnel)',
            widget=forms.TextInput(
                attrs={
                    'placeholder': 'Ex: AB12CD34',
                    'autocomplete': 'off',
                    'class': 'ibihub-auth-input',
                }
            ),
        )
        if self.initial.get('parrainage_code_input'):
            self.fields['parrainage_code_input'].initial = self.initial.get(
                'parrainage_code_input'
            )

        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        self.fields['password1'].label = 'Mot de passe'
        self.fields['password2'].label = 'Confirmation du mot de passe'
        self.fields['password1'].widget.attrs.setdefault('class', 'ibihub-auth-input')
        self.fields['password2'].widget.attrs.setdefault('class', 'ibihub-auth-input')

    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()

    def clean_telephone(self):
        raw = (self.cleaned_data.get('telephone') or '').strip()
        if not raw:
            return ''
        return raw

    def clean_parrainage_code_input(self):
        code = (self.cleaned_data.get('parrainage_code_input') or '').strip().upper()
        if not code:
            return ''
        if not UserCustom.objects.filter(code_parrainage__iexact=code).exists():
            raise forms.ValidationError('Code de parrainage invalide.')
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = user.username
        code = (self.cleaned_data.get('parrainage_code_input') or '').strip().upper()
        if code:
            parrain = UserCustom.objects.filter(code_parrainage__iexact=code).first()
            if parrain and parrain.pk != user.pk:
                user.parrain = parrain
        if commit:
            user.save()
        return user


class EntrepotAvisForm(forms.ModelForm):
    class Meta:
        model = EntrepotAvis
        fields = ('note', 'commentaire')
        labels = {
            'note': 'Note',
            'commentaire': 'Votre avis',
        }
        widgets = {
            'note': forms.Select(
                choices=[
                    (5, '5 — Excellent'),
                    (4, '4 — Très bien'),
                    (3, '3 — Bien'),
                    (2, '2 — Moyen'),
                    (1, '1 — Insuffisant'),
                ],
                attrs={'class': 'ibihub-space-avis-select'},
            ),
            'commentaire': forms.Textarea(
                attrs={
                    'rows': 4,
                    'class': 'ibihub-space-avis-textarea',
                    'placeholder': 'Décrivez votre expérience…',
                }
            ),
        }


class ContactForm(forms.Form):
    name = forms.CharField(
        label='Nom',
        max_length=120,
        widget=forms.TextInput(
            attrs={
                'class': 'ibihub-form__input',
                'autocomplete': 'name',
                'placeholder': 'Votre nom',
            }
        ),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(
            attrs={
                'class': 'ibihub-form__input',
                'autocomplete': 'email',
                'placeholder': 'vous@exemple.com',
            }
        ),
    )
    subject = forms.CharField(
        label='Sujet',
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'ibihub-form__input',
                'placeholder': 'Objet de votre message',
            }
        ),
    )
    message = forms.CharField(
        label='Message',
        widget=forms.Textarea(
            attrs={
                'rows': 6,
                'class': 'ibihub-form__textarea',
                'placeholder': 'Décrivez votre demande…',
            }
        ),
    )


RECLAMATION_TYPE_CHOICES = [
    ('transaction', 'Litige lié à une transaction ou réservation'),
    ('listing', 'Annonce inexacte ou trompeuse'),
    ('conduct', 'Comportement d’un utilisateur'),
    ('technical', 'Dysfonctionnement technique'),
    ('other', 'Autre'),
]


class ReclamationForm(forms.Form):
    type_reclamation = forms.ChoiceField(
        label='Type de réclamation',
        choices=[('', 'Choisir une catégorie')] + RECLAMATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'ibihub-form__select'}),
    )
    reference = forms.CharField(
        label='Référence (facultatif)',
        required=False,
        max_length=120,
        widget=forms.TextInput(
            attrs={
                'class': 'ibihub-form__input',
                'placeholder': 'N° d’annonce, de réservation…',
            }
        ),
    )
    subject = forms.CharField(
        label='Objet',
        max_length=200,
        widget=forms.TextInput(
            attrs={
                'class': 'ibihub-form__input',
                'placeholder': 'Résumé en une ligne',
            }
        ),
    )
    detail = forms.CharField(
        label='Description détaillée',
        widget=forms.Textarea(
            attrs={
                'rows': 7,
                'class': 'ibihub-form__textarea ibihub-form__textarea--large',
                'placeholder': 'Faits, dates, montants, échanges…',
            }
        ),
    )
    name = forms.CharField(
        label='Nom et prénom',
        max_length=120,
        widget=forms.TextInput(
            attrs={'class': 'ibihub-form__input', 'autocomplete': 'name'}
        ),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(
            attrs={
                'class': 'ibihub-form__input',
                'autocomplete': 'email',
                'placeholder': 'vous@exemple.com',
            }
        ),
    )
    phone = forms.CharField(
        label='Téléphone',
        required=False,
        max_length=40,
        widget=forms.TextInput(
            attrs={
                'class': 'ibihub-form__input',
                'placeholder': '+229 …',
                'autocomplete': 'tel',
            }
        ),
    )


EQUIPEMENT_CHOICES = [
    ('Gardiennage', 'Gardiennage'),
    ('Caméras de surveillance', 'Caméras de surveillance'),
    ('Électricité', 'Électricité'),
    ('Alarme / accès sécurisé', 'Alarme / accès sécurisé'),
    ('Zone frigo ou climatisation', 'Zone frigo ou climatisation'),
    ('Éclairage adapté', 'Éclairage adapté'),
    ('Internet / Wi‑Fi', 'Internet / Wi‑Fi'),
    ('Quai ou zone de chargement', 'Quai ou zone de chargement'),
]


class OwnerKycForm(forms.ModelForm):
    """Envoi pièce d’identité pour vérification du compte propriétaire."""

    class Meta:
        model = UserCustom
        fields = ('type_piece', 'piece_identite')
        labels = {
            'type_piece': 'Type de pièce',
            'piece_identite': 'Fichier (scan ou photo nette)',
        }
        widgets = {
            'type_piece': forms.Select(attrs={'class': 'ibihub-form__select'}),
            'piece_identite': forms.ClearableFileInput(
                attrs={'class': 'ibihub-form__input'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type_piece'].required = True
        self.fields['piece_identite'].required = True


class EntrepotForm(forms.ModelForm):
    """Équipements : cases à cocher + champ libre (pas de JSON)."""

    equipements_choices = forms.MultipleChoiceField(
        label='Équipements disponibles',
        choices=EQUIPEMENT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'ibihub-equipements-checkboxes'}
        ),
        help_text='Cochez tout ce qui s’applique à votre espace.',
    )
    equipements_autres = forms.CharField(
        required=False,
        label='Autres précisions',
        widget=forms.Textarea(
            attrs={
                'rows': 2,
                'class': 'ibihub-dashboard-textarea',
                'placeholder': 'Ex. : accès poids lourds, hauteur sous plafond 4 m',
            }
        ),
        help_text='Optionnel. Séparez les éléments par une virgule.',
    )

    class Meta:
        model = Entrepot
        fields = (
            'categorie',
            'titre',
            'description_detaillee',
            'adresse',
            'ville',
            'image_principale',
            'prix_par_jour',
            'surface_m2',
            'caution_requise',
            'montant_caution_fixe',
            'disponible',
        )
        labels = {
            'caution_requise': 'Caution requise',
            'montant_caution_fixe': 'Montant caution fixe (FCFA)',
        }
        widgets = {
            'description_detaillee': forms.Textarea(attrs={'rows': 5}),
            'prix_par_jour': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'titre': forms.TextInput(attrs={'placeholder': 'Ex. Entrepôt zone industrielle'}),
            'adresse': forms.TextInput(attrs={'placeholder': 'Quartier, rue…'}),
            'surface_m2': forms.NumberInput(attrs={'min': '1', 'placeholder': 'm²'}),
            'caution_requise': forms.CheckboxInput(),
            'montant_caution_fixe': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'min': '0',
                    'placeholder': 'Ex. 50000',
                }
            ),
            'categorie': forms.Select(),
            'ville': forms.Select(),
            'image_principale': forms.ClearableFileInput(),
            'disponible': forms.CheckboxInput(),
        }

    def __init__(self, *args, owner=None, **kwargs):
        self._owner = owner
        super().__init__(*args, **kwargs)
        preset = {k for k, _ in EQUIPEMENT_CHOICES}
        if self.instance.pk and self.instance.equipements:
            chosen = []
            autres = []
            for item in self.instance.equipements:
                if item in preset:
                    chosen.append(item)
                else:
                    autres.append(item)
            self.initial['equipements_choices'] = chosen
            if autres:
                self.initial['equipements_autres'] = ', '.join(autres)

    def clean(self):
        cleaned = super().clean()
        choices = cleaned.get('equipements_choices') or []
        autres_raw = (cleaned.get('equipements_autres') or '').strip()
        extras = []
        if autres_raw:
            for part in re.split(r'[,;\n]+', autres_raw):
                s = part.strip()
                if s:
                    extras.append(s)
        cleaned['_equipements_list'] = list(choices) + extras
        return cleaned

    def clean_disponible(self):
        disponible = self.cleaned_data.get('disponible')
        if disponible:
            owner = self._owner
            if owner is None and self.instance.pk:
                owner = getattr(self.instance, 'proprietaire', None)
            if owner is not None and not owner.is_verified:
                raise forms.ValidationError(
                    'Compte non vérifié : vous ne pouvez pas mettre l’annonce en ligne. '
                    'Transmettez votre pièce d’identité (menu Vérification du compte).'
                )
        return disponible

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.equipements = self.cleaned_data.get('_equipements_list') or []
        if commit:
            instance.save()
        return instance


class UserProfileForm(forms.ModelForm):
    """Paramètres du compte (tableau de bord)."""

    class Meta:
        model = UserCustom
        fields = (
            'first_name',
            'last_name',
            'email',
            'telephone',
            'photo_profil',
            'reseau_momo',
            'numero_momo',
        )
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'email': 'Adresse e-mail',
            'telephone': 'Téléphone',
            'photo_profil': 'Photo de profil',
            'reseau_momo': 'Réseau Mobile Money',
            'numero_momo': 'Numéro Mobile Money',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'telephone': forms.TextInput(
                attrs={
                    'autocomplete': 'tel',
                    'placeholder': '+229… (format international)',
                }
            ),
            'photo_profil': forms.ClearableFileInput(),
            'reseau_momo': forms.Select(),
            'numero_momo': forms.TextInput(
                attrs={'placeholder': '+229... (pour remboursements/gains)'}
            ),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = UserCustom.objects.exclude(pk=self.instance.pk).filter(username=email)
        if qs.exists():
            raise forms.ValidationError('Cette adresse e-mail est déjà utilisée.')
        return email

    def clean_telephone(self):
        raw = (self.cleaned_data.get('telephone') or '').strip()
        return raw

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = user.email.strip().lower()
        user.username = user.email
        if commit:
            user.save()
        return user


class EtatDesLieuxForm(forms.ModelForm):
    class Meta:
        model = EtatDesLieux
        fields = (
            'photo_entree_1',
            'photo_entree_2',
            'photo_sortie_1',
            'photo_sortie_2',
            'commentaire_proprietaire',
            'commentaire_commercant',
        )
        widgets = {
            'commentaire_proprietaire': forms.Textarea(attrs={'rows': 3}),
            'commentaire_commercant': forms.Textarea(attrs={'rows': 3}),
        }


class LitigeForm(forms.ModelForm):
    class Meta:
        model = Litige
        fields = ('motif', 'description')
        widgets = {
            'motif': forms.TextInput(attrs={'placeholder': 'Ex: refus de sortie sans motif'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class EntrepotIndisponibiliteForm(forms.ModelForm):
    class Meta:
        model = EntrepotIndisponibilite
        fields = ('entrepot', 'date_debut', 'date_fin', 'raison')
        widgets = {
            'date_debut': forms.DateInput(attrs={'type': 'date'}),
            'date_fin': forms.DateInput(attrs={'type': 'date'}),
            'raison': forms.TextInput(attrs={'placeholder': 'Maintenance, usage interne...'}),
        }

    def clean(self):
        cleaned = super().clean()
        d0 = cleaned.get('date_debut')
        d1 = cleaned.get('date_fin')
        if d0 and d1 and d1 < d0:
            raise forms.ValidationError('La date de fin doit être après la date de début.')
        return cleaned
