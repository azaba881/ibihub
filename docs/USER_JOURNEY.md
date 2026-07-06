# IbiHub — User Journey (Version Présentation)

IbiHub est une marketplace de stockage logistique qui connecte :
- 🧑‍💼 **Commerçants** (qui cherchent un espace)
- 🏬 **Propriétaires** (qui publient leurs espaces)
- 🛡️ **Administrateurs** (qui sécurisent et supervisent la plateforme)

---

## 🎯 Promesse IbiHub

- 🔒 **Sécurité d’abord** : KYC propriétaire obligatoire pour activer une annonce.
- ⚡ **Réservation simple** : dates, inventaire, confirmation fluide.
- 📄 **Cadre juridique sérieux** : contrat PDF généré automatiquement pour chaque réservation confirmée.

---

## 👤 Parcours Commerçant

### 1) Découvrir et choisir
- Recherche d’un entrepôt par ville, catégorie, budget.
- Consultation des fiches (prix, surface, équipements, avis, disponibilités).

### 2) Réserver facilement
- **Sans compte au préalable** : sur la fiche espace, saisie **nom + téléphone** (format international, ex. `+229…`), puis les mêmes étapes que pour un utilisateur connecté.
- Choix des dates (calendrier bloquant automatiquement les jours indisponibles).
- Saisie de l’inventaire de dépôt.
- Simulation rapide des m² nécessaires.
- Après validation, **compte créé automatiquement** si le téléphone est nouveau, puis **connexion automatique** ; l’utilisateur est invité à **définir son mot de passe** pour débloquer le pass d’accès (QR, PDF).

### 3) Comprendre le coût
- Prix total affiché clairement.
- Ligne **Caution** dynamique :
  - < 14 jours : **0 FCFA (Offert)**
  - ≥ 14 jours (si caution activée sur l’espace) : **montant fixe**

### 4) Exploiter la réservation
- Tant que le mot de passe n’est pas défini après une **réservation express**, le **QR Pass** et les **PDF** (ticket / contrat) restent masqués côté client ; un court formulaire permet de finaliser l’accès.
- Accès au **QR Pass** une fois le compte sécurisé.
- Téléchargement du **Contrat PDF** et du **ticket**.
- Suivi dans le dashboard jusqu’à la fin de location.

---

## 🏬 Parcours Propriétaire

### 1) Vérification KYC
- Upload pièce d’identité (CIP/CNI/Passeport).
- Validation par l’équipe IbiHub.
- Sans validation : annonce non activable en public.

### 2) Publication d’un espace
- Création annonce (adresse, prix/jour, surface, équipements, images).
- Paramétrage de la caution (requise/non, montant fixe).
- Définition de périodes verrouillées (maintenance, indisponibilité).

### 3) Pilotage activité
- Suivi des réservations et revenus.
- Contrat PDF accessible.
- Vue du taux d’occupation sur dashboard.

---

## 🛡️ Parcours Admin

### 1) Contrôle conformité
- Validation KYC des propriétaires.

### 2) Supervision financière
- Dashboard commissions mensuelles.

### 3) Gestion des cautions
- Liste des cautions actives.
- Action **"Libérer la caution"** en fin de processus logistique.

---

## ✅ Pourquoi c’est rassurant pour les partenaires

- **Confiance identité** : KYC des propriétaires.
- **Transparence financière** : coûts, commission, caution explicites.
- **Traçabilité contractuelle** : PDF généré automatiquement.
- **Contrôle opérationnel** : statut réservation + libération de caution administrée.

---

## 🆕 Mises à jour récentes

- ⚡ **Réservation express** : réserver depuis la fiche espace sans inscription préalable ; création de compte par téléphone + mur « définir le mot de passe » avant affichage du pass (QR / PDF).
- 🔁 **Compte unique, double usage** : un même utilisateur peut alterner entre mode **Commerçant** et mode **Propriétaire** depuis le dashboard.
- 💸 **Facturation** : Mobile Money (MTN/Moov), historique PDF.
- 📰 **Actualités** : articles publiés depuis l’admin (super-utilisateur), liste sur `/actualites/`.
- ⛔ **Indisponibilités propriétaire** : blocage de plages de dates visibles en rouge/grisé sur le calendrier.
- 📲 **Parcours terrain simplifié** : code court d’accès, actions rapides dépôt/retrait, support WhatsApp direct.
