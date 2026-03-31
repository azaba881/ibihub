# 📦 Ibihub - Plateforme de Partage d'Espaces de Stockage (Bénin)

**Ibihub** est une solution technologique conçue pour optimiser la logistique au Bénin. Elle permet aux propriétaires d'espaces sous-utilisés de monétiser leurs m² et aux commerçants de trouver des solutions de stockage flexibles, sécurisées et assurées.

---

## 🚀 Fonctionnalités Clés

### 🌍 Pour les Commerçants (Merchants)
- **Recherche localisée** : Trouver un espace à Cotonou, Calavi, Porto-Novo, etc.
- **Micro-Assurance automatique** : Chaque réservation inclut une protection de 5% du montant total.
- **Sécurité QR Code** : Un jeton unique généré à la confirmation pour sécuriser l'accès à l'entrepôt.

### 🏠 Pour les Propriétaires (Owners)
- **Gestion d'annonces** : Publication simplifiée avec photos et équipements (Caméras, Gardiennage, etc.).
- **Tableau de bord financier** : Suivi des revenus et des réservations en temps réel.
- **Vérification de compte** : Système `is_verified` pour garantir la qualité des partenaires.

---

## 🛠️ Stack Technique

- **Backend** : Django 5.0 (Python)
- **Modèle Utilisateur** : `UserCustom` (Email as username, Role-based)
- **Frontend** : Intégration modulaire du template **Listeo** (Django Templates + Partials)
- **Base de données** : SQLite (Dev) / PostgreSQL (Prod ready)
- **Sécurité** : `django-environ` (.env), `django-cleanup` (Media management)

---

## ⚙️ Installation & Configuration

### 1. Préparation de l'environnement
```bash
# Création de l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances
pip install -r requirements.txt


2. Configuration Variables d'Environnement
Créez un fichier .env à la racine du projet :

SECRET_KEY=votre_cle_secrete_django
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

3. Initialisation de la Base de Données

python manage.py migrate
python manage.py seed_ibihub  # Commande pour peupler les catégories de base
python manage.py createsuperuser


📂 Structure des Répertoires

config/ : Paramètres du projet et routage principal.

core/ : Logique métier (Modèles, Vues, Management Commands).

static/ : Assets CSS/JS/Images (Identité visuelle IbiHub via brand.css).

templates/ :

public/ : Pages vitrines et catalogue.

dashboard/ : Interfaces connectées.

layouts/ : Squelettes et composants réutilisables.

⚖️ Licence & Propriété

Développé par Innocent Kpade. Tous droits réservés. 2026.

### 💡 Note de ton Senior Dev :

Une fois ce fichier enregistré, ton projet est enfin "complet" au niveau de la documentation. Tu pourras maintenant attaquer sereinement la partie la plus excitante : **le tunnel de réservation public** pour que les commerçants puissent enfin louer leurs premiers espaces !

**Dis-moi quand tu es prêt à passer à l'action sur le formulaire de réservation !**