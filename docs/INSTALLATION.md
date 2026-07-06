# Installation rapide (3 étapes)

## 1) Créer et activer l’environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate
```

## 2) Installer les dépendances

```bash
pip install -r requirements.txt
```

## 3) Initialiser la base et lancer le serveur

```bash
python manage.py migrate
python manage.py seed_ibihub
python manage.py runserver
```

Après `migrate`, les migrations récentes sont appliquées automatiquement.
Le seed crée 3 catégories, un propriétaire test (`test_proprio` / `testproprio123`) et 5 entrepôts fictifs.

Application disponible sur : `http://127.0.0.1:8000/`

## Déploiement production

Voir [DEPLOY_FLY.md](DEPLOY_FLY.md) pour le déploiement sur Fly.io.

## Optionnel (tâches métier)

```bash
# Rappel des échéances mensuelles
python manage.py notify_renewals
```

## Après mise à jour du code

Toujours exécuter:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
```
