# Documentation Technique - IbiHub

## Réservation express (conversion)

- **Fiche espace** : un visiteur non connecté peut soumettre une réservation en renseignant **nom** + **téléphone** (en plus des dates et de l’inventaire).
- **Backend** (`reserver_espace`) : normalisation téléphone E.164 ; recherche d’un utilisateur existant par `telephone` ; sinon création `UserCustom` avec `username` = téléphone, mot de passe aléatoire, `must_set_password=True`, puis `login()`.
- **URLs** : `reservation/express/succes/`, `reservation/express/mot-de-passe/` pour la page de succès et le formulaire de mot de passe.
- **Sécurité produit** : tant que `must_set_password` est vrai, le client ne voit pas le QR dans le dashboard et ne peut pas télécharger ticket/contrat PDF ; redirection vers la page de définition de mot de passe si tentative de téléchargement.

## Nouvelles fonctions UX terrain

- **Code court d'accès**: chaque `Reservation` génère un code `ABC-123` (`code_court`) affiché en grand sur le dashboard commerçant.
- **Validation rapide propriétaire**: formulaire "Saisie rapide de code" pour confirmer une arrivée sans scan QR.
- **Inventaire image**: support `inventaire_photo` en plus de `inventaire_depot`.
- **Action directe**: boutons explicites `Entrée`, `Sortie`, `Mon reçu` pour réduire la charge cognitive.
- **WhatsApp global**: bouton flottant de support sur les layouts public et dashboard.

## Modèles ajoutés / enrichis

- `UserCustom`: `must_set_password` (mur d’accès pass PDF/QR pour comptes créés via réservation express).
- `Reservation`: `code_court`, `ticket_pdf`, `inventaire_photo`, `type_paiement`, `prochaine_echeance`, `checkin_at`, `checkout_at`.
- `Entrepot`: `is_boosted`, `boost_expires_at`.
- `EtatDesLieux`: photos entrée/sortie + commentaires + date de validation.
- `Litige`: déclaration, statut, décision admin.

## PDF

- Contrat complet maintenu (`contrat_pdf`).
- Ticket simplifié 1 page (`ticket_pdf`) généré automatiquement à la confirmation.

## Processus caution

- Restitution autorisée uniquement si les **2 photos de sortie** de l’état des lieux sont présentes.

## Paiement échelonné

- Option `MENSUEL` disponible sur la réservation.
- Commande de rappel: `python manage.py notify_renewals` (échéances J-3).

## Compatibilité legacy email

- Les anciens templates `templates/email/welcome.html` et `templates/email/reservation-confirmation.html`
  redirigent vers la nouvelle charte `templates/emails/...` pour supprimer les doublons.

## Mode dashboard multi-rôle

- Session `dashboard_mode` (`MERCHANT` / `OWNER`) avec bascule depuis la sidebar.
- Un compte peut combiner:
  - flux client (réservations, favoris),
  - flux propriétaire (entrepôts, disponibilités, revenus).
- La publication d’annonce reste protégée par `is_verified`.

## Blog / actualités

- Modèles `ArticleCategorie` et `Article` (titre, slug « nom de lecture », catégorie, chapô, contenu, image, publication).
- Rédaction réservée au **super-utilisateur** dans l’admin Django (`Article`, `ArticleCategorie`).
- Pages publiques : liste `/actualites/`, détail `/actualites/<slug>/`.
