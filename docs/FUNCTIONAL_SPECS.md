# IbiHub — Functional Specifications (Version Technique)

## 1. Scope

Ce document formalise les fonctionnalités cœur pour :
- `MERCHANT` (commerçant)
- `OWNER` (propriétaire)
- `STAFF/ADMIN` (administration)

---

## 2. Functional Matrix

| Fonctionnalité | Merchant | Owner | Admin |
|---|:---:|:---:|:---:|
| Inscription / connexion | ✅ | ✅ | ✅ |
| Connexion email/téléphone | ✅ | ✅ | ✅ |
| Recherche d’espaces | ✅ | ✅ | ⛔ |
| Réservation | ✅ | ⛔ | ⛔ |
| Inventaire de dépôt | ✅ (saisie) | 👁️ | 👁️ |
| QR Pass accès | ✅ | 👁️ | ⛔ |
| Contrat PDF | ✅ | ✅ | ✅ |
| Upload KYC | ⛔ | ✅ | ⛔ |
| Validation KYC | ⛔ | ⛔ | ✅ |
| Création/édition entrepôt | ⛔ | ✅ | ✅ |
| Verrouillage périodes | ⛔ | ✅ | ✅ |
| Paramétrage caution | ⛔ | ✅ | ✅ |
| Libération caution | ⛔ | ⛔ | ✅ |
| Analytics commissions | ⛔ | ⛔ | ✅ |
| Taux d’occupation | ⛔ | ✅ | ✅ |

---

## 3. Reservation Lifecycle

### 3.1 Statuts
`EN_ATTENTE` → `CONFIRME` → `TERMINE` / `ANNULE`

### 3.2 Transitions
- **Création** : selon flux actif, réservation enregistrée puis contrôles métier appliqués.
- **Confirmation** : génération QR (si absent) + génération contrat PDF.
- **Annulation** : statut `ANNULE`.
- **Fin de cycle** : statut `TERMINE`.

---

## 4. Caution Rule (Business Logic)

### 4.1 Paramètres Entrepot
- `caution_requise` (booléen)
- `montant_caution_fixe` (montant FCFA)

### 4.2 Règle de calcul
Soit `duree = (date_fin - date_debut) + 1` (jours inclusifs)

```text
SI caution_requise == True ET duree >= 14
    montant_caution = montant_caution_fixe
SINON
    montant_caution = 0
```

### 4.3 Rendu opérationnel
- Champ `montant_caution` calculé au `save()` de `Reservation`.
- Champ `caution_rendue` piloté par l’admin via action “Libérer la caution”.

---

## 5. Pricing Components

- `montant_total = prix_par_jour * duree`
- `frais_assurance = montant_total * IBIHUB_COMMISSION_RATE`
- `revenu_net_proprietaire = montant_total - frais_assurance`
- `montant_caution` selon règle section 4.

Tous les calculs financiers utilisent `Decimal`.

---

## 6. Contract & Compliance

- Contrat PDF généré automatiquement pour réservation confirmée.
- Disponible au téléchargement côté merchant et owner.
- KYC obligatoire pour qu’un owner puisse exploiter une annonce en public.

---

## 7. Edge Cases

### 7.1 Owner non vérifié (`is_verified = False`)
- Création de compte possible.
- Accès dashboard possible.
- Upload KYC possible.
- **Blocage visibilité publique annonce** :
  - une annonce ne doit pas être visible/publicable si owner non vérifié,
  - impossibilité de forcer `disponible=True` côté métier.

### 7.2 Caution non applicable
- Si durée < 14 jours, caution = `0` même si `caution_requise=True`.

### 7.3 Libération caution répétée
- Si `caution_rendue=True`, l’action admin ne doit pas réappliquer la libération (idempotence logique).

---

## 8. Admin Controls

- Dashboard commissions par mois.
- Tableau des cautions actives.
- Action POST sécurisée : `Libérer la caution`.

---

## 9. Nouveautés (Q2 2026)

### 9.1 Multi-mode utilisateur (Merchant + Owner)
- Champ `can_post_announcements` sur `UserCustom`.
- Mode dashboard en session : `request.session['dashboard_mode']` (`MERCHANT` / `OWNER`).
- Sidebar dynamique selon mode actif.
- Si passage en mode propriétaire sans KYC validé : page intermédiaire KYC + blocage publication.

### 9.2 Parrainage automatisé
- Gain fixe : **500 FCFA**.
- Déclencheur : `Reservation` passe à `TERMINE`.
- Condition : client possède un `parrain`.
- Anti-doublon :
  - `Reservation.gain_parrainage_verse = True` après versement,
  - historique `ParrainageGain` (une entrée par réservation).
- Règle produit : versement sur la **première réservation terminée** du filleul.

### 9.3 Facturation
- Nouveaux champs profil:
  - `reseau_momo` (`MTN` / `MOOV`)
  - `numero_momo` (E.164)
  - `solde_parrainage`
- Onglet facturation dashboard:
  - historique factures PDF,
  - historique gains parrainage,
  - solde cumulé.
