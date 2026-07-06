# Déploiement IbiHub sur Fly.io

## Prérequis

- Compte [Fly.io](https://fly.io)
- CLI installée : `curl -L https://fly.io/install.sh | sh`
- Connexion : `fly auth login`

## 1. Créer l'application

```bash
# Renommez l'app dans fly.toml si besoin (nom unique globalement)
fly apps create ibihub --org personal
```

## 2. Base PostgreSQL

```bash
fly postgres create --name ibihub-db --region cdg
fly postgres attach ibihub-db --app ibihub
```

La variable `DATABASE_URL` est injectée automatiquement.

## 3. Secrets & configuration

```bash
fly secrets set \
  SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(50))')" \
  DEBUG=False \
  ALLOWED_HOSTS=ibihub.fly.dev \
  SITE_URL=https://ibihub.fly.dev \
  CSRF_TRUSTED_ORIGINS=https://ibihub.fly.dev \
  DEFAULT_FROM_EMAIL="IbiHub <noreply@ibihub.bj>" \
  CONTACT_RECIPIENT_EMAIL=contact@ibihub.bj \
  MEDIA_ROOT=/data/media
```

Configurer SMTP (ex. Resend, SendGrid, Brevo) :

```bash
fly secrets set \
  EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend \
  EMAIL_HOST=smtp.resend.com \
  EMAIL_PORT=587 \
  EMAIL_USE_TLS=True \
  EMAIL_HOST_USER=resend \
  EMAIL_HOST_PASSWORD=re_xxxxxxxx
```

## 4. Volume pour les fichiers média

```bash
fly volumes create ibihub_media --region cdg --size 1
```

Le volume est monté sur `/data/media` (voir `fly.toml`).

## 5. Déployer

```bash
fly deploy
```

## 6. Créer un superutilisateur

```bash
fly ssh console -C "python manage.py createsuperuser"
fly ssh console -C "python manage.py seed_ibihub"
```

## 7. Domaine personnalisé (optionnel)

```bash
fly certs add ibihub.bj
fly secrets set ALLOWED_HOSTS=ibihub.bj,ibihub.fly.dev SITE_URL=https://ibihub.bj CSRF_TRUSTED_ORIGINS=https://ibihub.bj
```

## Commandes utiles

```bash
fly status
fly logs
fly ssh console
fly scale count 1   # garder une machine toujours active
```

## Notes production

| Sujet | Recommandation |
|-------|----------------|
| **Médias** | Volume Fly pour démarrer ; migrer vers Tigris/S3 pour la haute dispo |
| **E-mails** | SMTP transactionnel (Resend, Brevo) — ne pas utiliser Maildev |
| **Statiques** | WhiteNoise + `collectstatic` dans le Dockerfile |
| **Tâches planifiées** | `fly machine run` ou cron externe pour `notify_renewals` |
| **Backups DB** | `fly postgres backup list -a ibihub-db` |
