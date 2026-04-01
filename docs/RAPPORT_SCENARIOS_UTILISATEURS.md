# Rapport scénarios utilisateurs — IbiHub

Ce document décrit les parcours complets des utilisateurs, **de l’inscription à la dernière action métier**.

---

## 1. Scénario Commerçant (MERCHANT)

### 1.1 Objectif utilisateur
Trouver un espace de stockage adapté, réserver, déposer ses marchandises, suivre son dossier jusqu’à clôture.

### 1.2 Parcours complet (de bout en bout)
1. **Inscription**
   - Le commerçant crée un compte avec e-mail, téléphone, mot de passe.
   - Le rôle est `MERCHANT`.

2. **Connexion**
   - Authentification via e-mail ou téléphone + mot de passe.

3. **Recherche d’espace**
   - Navigation sur l’accueil/liste des espaces.
   - Filtrage par ville, catégorie, budget.

4. **Consultation fiche espace**
   - Vérification du prix/jour, surface, équipements, calendrier de disponibilité, avis.

5. **Pré-réservation**
   - Saisie date début / date fin.
   - Saisie inventaire de dépôt (marchandises).
   - Usage du simulateur m² (cartons/sacs).
   - Visualisation de la caution dynamique:
     - moins de 14 jours: `0 FCFA (Offert)`
     - 14 jours et plus (si caution activée sur l’entrepôt): montant caution fixe.

6. **Réservation**
   - Envoi du formulaire.
   - Contrôles backend: validité dates, indisponibilités, règles métier.
   - Calcul automatique: montant total, commission, caution, revenu net propriétaire.

7. **Après confirmation**
   - Attribution d’un QR d’accès (si réservation confirmée).
   - Génération automatique du contrat PDF.

8. **Suivi dashboard commerçant**
   - Consultation des réservations, statuts, inventaire, QR, contrat PDF.

9. **Fin de cycle**
   - Réservation terminée.
   - Caution potentiellement libérée par l’admin selon processus de sortie.

### 1.3 Dernière action métier (commerçant)
- Télécharger le contrat PDF, utiliser le pass QR, clôturer le cycle de stockage.

---

## 2. Scénario Propriétaire (OWNER)

### 2.1 Objectif utilisateur
Publier et exploiter des espaces de stockage en sécurité, gérer les disponibilités et suivre les revenus.

### 2.2 Parcours complet (de bout en bout)
1. **Inscription / Connexion**
   - Création ou accès au compte propriétaire.

2. **KYC (vérification d’identité)**
   - Tant que `is_verified = False`, l’utilisateur voit la bannière “Compte non vérifié”.
   - Soumission du type de pièce (CIP/CNI/Passeport) + upload de pièce d’identité.

3. **Validation KYC par équipe IbiHub**
   - Passage du compte en vérifié.

4. **Création d’annonce**
   - Saisie des informations de l’entrepôt (adresse, prix/jour, surface, équipements, images).
   - Paramétrage caution:
     - `caution_requise` (oui/non)
     - `montant_caution_fixe`

5. **Mise en ligne**
   - `disponible=True` seulement si compte vérifié.

6. **Gestion des indisponibilités**
   - Définition de jours/périodes verrouillés (maintenance, usage perso).

7. **Suivi des réservations**
   - Vue des demandes/historiques, statuts, montants, commission, caution, revenu net.
   - Accès au contrat PDF.

8. **Pilotage activité**
   - Consultation des indicateurs du dashboard.
   - Lecture du graphique de taux d’occupation.

### 2.3 Dernière action métier (propriétaire)
- Finaliser les cycles de location et analyser la performance (occupation + revenus).

---

## 3. Scénario Administrateur (STAFF/ADMIN)

### 3.1 Objectif utilisateur
Assurer conformité, sécurité, qualité de service et clôture financière des opérations.

### 3.2 Parcours complet (de bout en bout)
1. **Connexion administration**
   - Accès aux vues staff/dashboard admin.

2. **Validation KYC**
   - Contrôle des documents transmis.
   - Activation `is_verified` des propriétaires conformes.

3. **Supervision financière**
   - Consultation des commissions mensuelles (`frais_assurance`).

4. **Gestion cautions**
   - Liste des cautions non rendues.
   - Action “Libérer la caution” pour marquer `caution_rendue=True`.

5. **Suivi global plateforme**
   - Contrôle des réservations, incidents, cohérence métier.

### 3.3 Dernière action métier (admin)
- Clôturer les dossiers logistiques/financiers en libérant les cautions éligibles.

---

## 4. Matrice actions par rôle

| Fonctionnalité | Commerçant | Propriétaire | Admin |
|---|:---:|:---:|:---:|
| Inscription / connexion | Oui | Oui | Oui |
| Connexion e-mail/téléphone | Oui | Oui | Oui |
| Recherche d’espaces | Oui | Oui | Non critique |
| Réservation | Oui | Non | Non |
| Inventaire dépôt | Oui | Consultation | Consultation |
| QR d’accès | Oui | Visualisation indirecte | Non |
| Contrat PDF | Oui | Oui | Oui |
| Upload KYC | Non | Oui | Non |
| Validation KYC | Non | Non | Oui |
| Création/édition entrepôt | Non | Oui | Oui (admin) |
| Verrouillage périodes | Non | Oui | Oui |
| Paramétrage caution | Non | Oui | Oui |
| Libération caution | Non | Non | Oui |
| Analytics commissions | Non | Non | Oui |
| Taux d’occupation | Non | Oui | Oui |

---

## 5. Règles métier clés (rappel)

- Une réservation doit respecter les disponibilités réelles (réservations existantes + périodes verrouillées).
- La caution est appliquée seulement si:
  - l’entrepôt a `caution_requise=True`
  - et la durée de réservation est `>= 14` jours.
- Sinon, caution à `0 FCFA (Offert)`.
- Le statut de restitution de caution est tracé par `caution_rendue`.

---

## 6. Résumé exécutif

IbiHub orchestre trois parcours complémentaires:
- **Commerçant**: découverte → réservation → exécution → clôture.
- **Propriétaire**: KYC → publication → gestion opérationnelle → pilotage.
- **Admin**: conformité KYC + supervision financière + clôture des cautions.

L’ensemble garantit une marketplace de stockage structurée, traçable et sécurisée.

---

## 7. Addendum — Parcours multi-rôle (même compte)

### 7.1 Objectif
Permettre à un utilisateur d’opérer comme commerçant **et** propriétaire sans créer un second compte.

### 7.2 Parcours
1. L’utilisateur (initialement commerçant) clique sur **Passer en mode Propriétaire**.
2. Le mode dashboard est mémorisé en session (`dashboard_mode`).
3. Si KYC non validé:
   - affichage d’une page intermédiaire KYC,
   - accès publication bloqué.
4. Après vérification admin (`is_verified=True`):
   - accès complet aux menus propriétaire,
   - création d’annonce autorisée.
5. L’utilisateur peut revenir en mode commerçant à tout moment.

### 7.3 Impact UX
- Sidebar contextualisée au mode actif.
- Notifications de gains (parrainage / loyers) visibles quel que soit le mode.
