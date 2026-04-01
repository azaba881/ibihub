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
python manage.py runserver
```

Application disponible sur : `http://127.0.0.1:8000/`

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
