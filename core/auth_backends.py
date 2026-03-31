"""Authentification par e-mail (username) ou numéro de téléphone (E.164, ex. +229…)."""

from django.contrib.auth.backends import ModelBackend

from .models import UserCustom


def _digits_only(s: str) -> str:
    return ''.join(c for c in (s or '') if c.isdigit())


def _phone_lookup_candidates(raw: str) -> list[str]:
    """
    Produit des variantes E.164 à tester pour le Bénin (+229).
    Ex. : 97123456 → +22997123456 ; +22997123456 → inchangé ; 22997123456 → +22997123456
    """
    s = (raw or '').strip().replace(' ', '').replace('-', '')
    candidates: list[str] = []
    if s.startswith('+'):
        candidates.append(s)
    d = _digits_only(s)
    if not d:
        return list(dict.fromkeys(candidates))

    # Déjà en forme 229 + 8 chiffres nationaux (11 chiffres)
    if len(d) >= 11 and d.startswith('229'):
        candidates.append('+' + d[:11])

    # 8 chiffres seuls : numéro national Bénin
    if len(d) == 8:
        candidates.append('+229' + d)

    # Suffixe 8 derniers chiffres (saisie partielle type 97… ou 96…)
    if len(d) >= 8:
        candidates.append('+229' + d[-8:])

    # Sans indicatif : 10 chiffres commençant par 0 (ex. 01…)
    if len(d) == 10 and d.startswith('0'):
        candidates.append('+229' + d[-8:])

    return list(dict.fromkeys(c for c in candidates if c))


class EmailOrPhoneBackend(ModelBackend):
    """Connexion avec l’e-mail (username) ou le téléphone stocké en base."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        username = username.strip()
        if not username:
            return None

        user = None

        if '@' in username:
            email = username.lower()
            try:
                user = UserCustom.objects.get(username__iexact=email)
            except UserCustom.DoesNotExist:
                return None
        else:
            for phone in _phone_lookup_candidates(username):
                try:
                    user = UserCustom.objects.get(telephone=phone)
                    break
                except UserCustom.DoesNotExist:
                    continue
            if user is None:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
