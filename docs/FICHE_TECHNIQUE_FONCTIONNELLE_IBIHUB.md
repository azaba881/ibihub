# Fiche technique & fonctionnelle — IbiHub

**Version du document :** 1.0  
**Périmètre :** application web marketplace de stockage logistique (Bénin).  
**Référence codebase :** Django 5.2.x, déploiement cible Python 3.12 / PostgreSQL ; développement local SQLite.

---

## 1. Vision & objectifs

### 1.1 Concept

**IbiHub** est une **marketplace de mise en relation** entre **propriétaires d’espaces de stockage** (entrepôts, box, surfaces logistiques) et **commerçants** ayant besoin de capacité temporaire ou récurrente au **Bénin**. La plateforme vise à digitaliser la découverte des offres, la structuration des annonces (surface, équipements, localisation) et le cycle de **réservation** avec traçabilité (statuts, assurance plateforme, accès QR).

### 1.2 Objectifs métier

| Objectif | Description |
|----------|-------------|
| Liquidité du marché | Mettre en visibilité des capacités sous-utilisées. |
| Confiance | Comptes vérifiés pour publication, avis clients, règles de disponibilité. |
| Traçabilité financière | Montant de location, micro-assurance (5 %), revenu net propriétaire explicite. |
| Accès terrain | Pass numérique (QR) lié à la réservation confirmée. |

### 1.3 Cibles utilisateurs

| Rôle | Code métier | Besoins principaux |
|------|-------------|-------------------|
| **Commerçant** | `MERCHANT` | Rechercher un espace, réserver, suivre réservations / QR, tableau de bord dépenses & séjours actifs. |
| **Propriétaire** | `OWNER` | Publier / éditer des annonces (sous validation `is_verified`), gérer disponibilités (blocages), traiter demandes en attente le cas échéant, suivre CA et revenus. |

---

## 2. Architecture technique

### 2.1 Stack cible & réalisée

| Couche | Choix documentaire (cible prod) | État projet (référence) |
|--------|----------------------------------|-------------------------|
| Langage | Python 3.12 | Compatible 3.10+ (venv courant) |
| Framework | Django 5.0+ | **Django 5.2.x** (`requirements.txt`) |
| Base de données | **PostgreSQL** (production) | **SQLite** (`db.sqlite3`) en dev |
| Fichiers statiques | Collecte Django / CDN ponctuel | `STATICFILES_DIRS`, thème Listeo + overrides |
| Médias | File system (+ extension cloud) | `MEDIA_ROOT` / `FileSystemStorage` |

**Bibliothèques notables :** `Pillow` (images), `qrcode` (génération QR), `django-environ` (configuration), `django-cleanup` (nettoyage fichiers orphelins), `djangorestframework` (installé ; **cœur métier V1 majoritairement vues Django**, API REST non centrée sur le parcours public).

### 2.2 Frontend

| Élément | Détails |
|---------|---------|
| Moteur de rendu | **Templates Django** (héritage `base.html`, blocs `content`, `extra_css`, `extra_js`). |
| Thème / intégration | Base **Listeo** (CSS/JS hérités : jQuery, Slick, Leaflet, etc.). |
| Identité visuelle | Couches **`brand.css`**, `ibihub-*.css`, `ibihub-pages.css` (composants dashboard, hero, formulaires). |
| JavaScript | jQuery et scripts thème ; **intl-tel-input** sur l’inscription (normalisation saisie téléphone). |
| Calendrier réservation | **Flatpickr** (CDN) sur fiche espace : jours indisponibles injectés en JSON. |

### 2.3 Sécurité

| Mécanisme | Implémentation |
|-----------|----------------|
| Authentification | Sessions Django ; backend personnalisé **email ou téléphone** + `ModelBackend` en secours. |
| Mots de passe | Hachage **PBKDF2** (défaut Django `AbstractUser`). |
| CSRF | `CsrfViewMiddleware` + `{% csrf_token %}` sur formulaires POST. |
| XSS | Échappement templates Django ; contenus utilisateur affichés via filtres par défaut. |
| Rôles | **Pas de middleware dédié « restriction de rôle »** : contrôle dans **vues** (`request.user.role`), **mixins** (`LoginRequiredMixin`) et redirections (ex. espaces réservés aux `OWNER`). |
| Compte vérifié | `UserCustom.is_verified` : requis pour **création / édition d’annonce** (sinon message + redirection). |
| Actions sensibles | Ex. `require_POST` pour confirmation / annulation réservation, contrôle propriétaire ou client selon cas. |

### 2.4 Stockage des médias

- **Actuel :** fichiers sur disque (`MEDIA_ROOT`), champs `ImageField` (`profiles/`, `entrepots/`, `categories/`, galerie).
- **Évolution :** abstraction compatible **S3** (django-storages) ou **Cloudinary** sans changer le modèle : substitution du backend de stockage dans `settings`.

### 2.5 Configuration & environnement

- Variables via **django-environ** (`.env`) : `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, e-mail (SMTP / Maildev), etc.
- Timezone : `UTC` en settings (à ajuster pour affichage local si besoin).

---

## 3. Spécifications fonctionnelles (cœur métier)

### 3.1 Authentification & comptes

- **Inscription :** rôle (souvent commerçant par défaut), username e-mail, téléphone **E.164** (+229…), mot de passe.
- **Connexion hybride :** identifiant = **e-mail** (`username`) ou **numéro** (variantes Bénin normalisées côté backend).
- **Profil :** mise à jour nom, e-mail, téléphone, **photo de profil** (`photo_profil`).
- **Vérification :** flag `is_verified` géré côté **admin** ; bloque la publication d’espaces tant que `False`.

### 3.2 Annonces (entrepôts)

- **Fiche :** titre, description, adresse, **ville** (liste contrôlée : Cotonou, Porto-Novo, Parakou, Bohicon, Abomey-Calavi), surface, prix/jour, catégorie, image principale.
- **Galerie :** N images (`EntrepotImage`, ordre d’affichage).
- **Équipements :** liste JSON (ex. gardiennage, caméras, électricité, zone frigo…).
- **Disponibilité annonce :** booléen `disponible` ; **périodes bloquées** (`EntrepotPeriodeBloquee`) éditables inline admin / propriétaire selon configuration.
- **Géolocalisation :** granularité **ville** (pas de lat/lng obligatoire dans le modèle V1) ; cartes Leaflet possibles côté thème pour listing.

### 3.3 Réservations

**Calcul de durée**

- Durée en jours = **inclusive** : `(date_fin - date_debut).days + 1`, minimum 1 jour (`Reservation.calcule_duree_jours`).

**Tarification**

- **Prix linéaire :** `montant_total = nombre_de_jours × entrepot.prix_par_jour` (arrondi décimal).
- **Prix dégressif :** **non implémenté** dans le modèle actuel ; évolution V2 possible (paliers, remises longue durée).

**Micro-assurance**

- Taux configurable **`settings.IBIHUB_COMMISSION_RATE`** (défaut **5 %**) sur `montant_total`.
- `frais_assurance = montant_total × taux` ; recalcul au `save()` en `Decimal`.
- **Revenu net propriétaire :** champ `revenu_net_proprietaire` = `montant_total - frais_assurance` (mis à jour à chaque `save()`).

**Disponibilité calendaire**

- Indisponibilités = chevauchement avec réservations **EN_ATTENTE** ou **CONFIRME** + **périodes bloquées**.
- Vérification serveur : `booking_range_unavailable` ; côté client : Flatpickr avec liste de dates désactivées.

**Flux de statut**

- Création depuis la fiche espace : statut **`CONFIRME`** si créneau libre (confirmation immédiate, sous réserve des règles métier actuelles).
- Statut **`EN_ATTENTE`** conservé dans le modèle : le propriétaire peut **confirmer / refuser** depuis le tableau de bord pour les demandes encore en attente (flux legacy ou manuel).
- **`TERMINE` / `ANNULE` :** fin de cycle ou annulation contrôlée.

**QR Code (pass d’accès)**

- Lorsque `statut == CONFIRME`, génération d’un **slug unique** `qr_code_auth` si absent.
- Affichage en **data URI** (PNG) pour le client / le tableau de bord.

### 3.4 Autres parcours publics

- **Contact / réclamation :** formulaires e-mail vers `CONTACT_RECIPIENT_EMAIL`, pages de confirmation.
- **Avis :** un avis par utilisateur et par entrepôt (`EntrepotAvis`), note + commentaire.
- **Pages légales :** CGU, confidentialité, sécurité des espaces.

### 3.5 Tableaux de bord

- **Propriétaire :** cartes statistiques (nombre d’entrepôts, CA réservations terminées, montant réservations confirmées non terminées), raccourcis espaces / réservations.
- **Commerçant :** cartes alignées (réservations actives, total dépensé sur terminées, montant cumulé des séjours actifs), liste des réservations en cours (aperçu), lien vers historique complet.

---

## 4. Schéma de données (modèles & relations)

### 4.1 Vue d’ensemble (textuelle)

```
UserCustom (1) ──< (N) Entrepot [proprietaire]
CategorieStorage (1) ──< (N) Entrepot [categorie, PROTECT]

Entrepot (1) ──< (N) EntrepotImage
Entrepot (1) ──< (N) EntrepotPeriodeBloquee
Entrepot (1) ──< (N) Reservation
Entrepot (1) ──< (N) EntrepotAvis

UserCustom (1) ──< (N) Reservation [client]
UserCustom (1) ──< (N) EntrepotAvis [auteur]
```

### 4.2 Rôles des entités clés

| Modèle | Rôle |
|--------|------|
| **UserCustom** | Utilisateur Django étendu : `role`, `telephone`, `photo_profil`, `is_verified`. |
| **CategorieStorage** | Taxonomie métier (nom, icône Font Awesome, image optionnelle). |
| **Entrepot** | Annonce d’espace : lien propriétaire + catégorie, prix/jour, JSON équipements, ville, médias. |
| **EntrepotImage** | Galerie ordonnée rattachée à un entrepôt. |
| **EntrepotPeriodeBloquee** | Fermetures manuelles (maintenance, usage perso) impactant la disponibilité. |
| **Reservation** | Contrat de location : client, entrepôt, dates, montants, assurance, statut, `qr_code_auth`. |
| **EntrepotAvis** | Note et commentaire ; contrainte d’unicité `(entrepot, auteur)`. |

---

## 5. Interface & responsivité (UX)

### 5.1 Navigation

- **Header** : menu principal ; sur mobile, comportement type **overlay / menu plein écran** selon thème Listeo + styles IbiHub (`mmenu` / patterns existants).
- **Dashboard** : layout dédié (`base_dashboard.html`), sidebar avec entrées conditionnées au rôle.

### 5.2 Listing & grilles

- Grille de cartes **adaptative** : colonnes variables selon breakpoints (viser **3 / 2 / 1** colonnes d’affichage sur largeur décroissante), cohérent avec Bootstrap / classes thème.

### 5.3 Dashboard différencié

- **Contenu, statistiques et actions** distincts pour **OWNER** vs **MERCHANT** (templates conditionnels `is_owner`).
- **Formulaires** : cartes (`ibihub-form-card`), tableaux de bord avec états vides explicites.

### 5.4 Fiche espace

- Hero + détails + calendrier de disponibilité (légende réservation vs fermeture) + formulaire réservation (Flatpickr) pour utilisateurs éligibles (non propriétaire, connecté, espace disponible).

---

## 6. Roadmap technique (V2)

| Thème | Objectifs |
|-------|-----------|
| **Paiement** | Intégration **FedaPay** / **KkiaPay** (ou équivalent local) : intention de paiement, webhook, statut réservation lié au paiement réussi, éventuellement acompte / caution. |
| **Messagerie** | Canal **temps réel** (WebSockets / Django Channels ou service tiers) entre commerçant et propriétaire, lié à une réservation ou une annonce. |
| **PWA / mobile** | **Progressive Web App** : manifest, service worker, mode hors-ligne partiel, raccourci « installer l’app » ; base pour future app native ou Capacitor. |
| **Tarification avancée** | **Prix dégressif** par tranche de jours, saisonnalité, minimum de nuitées. |
| **API** | Exposer **REST** ou **GraphQL** pour applications mobiles et partenaires (DRF déjà présent). |
| **Observabilité** | Logs structurés, monitoring (Sentry), sauvegardes PostgreSQL automatisées. |

---

## 7. Glossaire rapide

| Terme | Définition |
|-------|------------|
| Micro-assurance | Prélèvement forfaitaire de 5 % sur le montant de la location, stocké en `frais_assurance`. |
| E.164 | Format international du numéro (ex. `+22997123456`). |
| Pass QR | Slug unique `qr_code_auth` matérialisé en QR pour contrôle d’accès logistique. |

---

*Document rédigé pour cadrage produit / technique ; à maintenir à chaque évolution majeure du domaine métier ou de l’infrastructure.*

---

## 8. Mise à jour fonctionnelle (2026)

### 8.1 Compte unique, double rôle
- Extension du modèle utilisateur pour activer l’usage propriétaire sans changer de compte.
- Bascule d’interface via mode dashboard en session.
- Menus dashboard filtrés selon le mode actif (client vs propriétaire).

### 8.2 Monétisation & facturation
- Section tarifs sur l’accueil (`Découverte`, `Pro`, `Entreprise`).
- Onglet facturation: Mobile Money, factures PDF, solde parrainage.
- WhatsApp support unifié (numéro officiel configuré).

### 8.3 Parrainage automatisé
- Récompense parrain: `500 FCFA` sur première réservation terminée du filleul.
- Historisation dédiée (`ParrainageGain`) et message de notification en dashboard.

### 8.4 Opérations logistiques avancées
- Indisponibilités propriétaire via dashboard + calendrier.
- Code court d’accès, ticket PDF simplifié, actions terrain check-in/check-out.
