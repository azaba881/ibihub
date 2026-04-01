# Documentation Technique - IbiHub

## Nouvelles fonctions UX terrain

- **Code court d'accès**: chaque `Reservation` génère un code `ABC-123` (`code_court`) affiché en grand sur le dashboard commerçant.
- **Validation rapide propriétaire**: formulaire "Saisie rapide de code" pour confirmer une arrivée sans scan QR.
- **Inventaire image**: support `inventaire_photo` en plus de `inventaire_depot`.
- **Action directe**: boutons explicites `Entrée`, `Sortie`, `Mon reçu` pour réduire la charge cognitive.
- **WhatsApp global**: bouton flottant de support sur les layouts public et dashboard.

## Modèles ajoutés / enrichis

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
  - flux client (réservations, favoris, parrainage),
  - flux propriétaire (entrepôts, disponibilités, revenus).
- La publication d’annonce reste protégée par `is_verified`.

## Parrainage automatisé

- Signal `post_save` sur `Reservation`:
  - si statut `TERMINE` + client parrainé,
  - crédit `+500 FCFA` au parrain,
  - écriture d’historique `ParrainageGain`,
  - verrou anti-doublon `gain_parrainage_verse=True`.
- Notification en dashboard au parrain lors de sa prochaine session.
