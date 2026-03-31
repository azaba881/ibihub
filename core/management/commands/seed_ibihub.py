import base64
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.models import CategorieStorage, Entrepot, UserCustom

# PNG 1×1 transparent (valide pour ImageField si aucune image statique)
_MIN_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)


def _seed_image_bytes():
    for rel in (
        'static/images/category-space/cat-1.png',
        'static/images/logo.png',
    ):
        p = Path(settings.BASE_DIR) / rel
        if p.is_file():
            return p.read_bytes(), p.name
    return _MIN_PNG, 'placeholder.png'


class Command(BaseCommand):
    help = 'Crée des données de test : catégories, utilisateur propriétaire, entrepôts fictifs.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-entrepots',
            action='store_true',
            help='Supprime les entrepôts existants du compte test_proprio avant de recréer.',
        )

    def handle(self, *args, **options):
        categories_data = [
            ('Magasin Sec', 'fa-store'),
            ('Chambre Froide', 'fa-snowflake'),
            ('Garage Sécurisé', 'fa-shield-alt'),
        ]
        categories = []
        for nom, icone in categories_data:
            cat, created = CategorieStorage.objects.get_or_create(
                nom=nom,
                defaults={'icone': icone},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Catégorie créée : {nom}'))
            else:
                self.stdout.write(f'Catégorie existante : {nom}')
            categories.append(cat)

        user, created = UserCustom.objects.get_or_create(
            username='test_proprio',
            defaults={
                'email': 'test_proprio@ibihub.local',
                'role': 'OWNER',
                'first_name': 'Test',
                'last_name': 'Propriétaire',
                'telephone': '01 97 12 34 56',
            },
        )
        user.role = 'OWNER'
        user.set_password('testproprio123')
        user.save()
        if created:
            self.stdout.write(self.style.SUCCESS(
                "Utilisateur créé : test_proprio (mot de passe : testproprio123)"
            ))
        else:
            self.stdout.write(
                "Utilisateur test_proprio mis à jour (mot de passe : testproprio123)"
            )

        existing = Entrepot.objects.filter(proprietaire=user).count()
        if existing and not options['reset_entrepots']:
            self.stdout.write(self.style.WARNING(
                f'{existing} entrepôt(s) déjà présent(s) pour test_proprio. '
                'Utilisez --reset-entrepots pour supprimer et recréer les 5 entrepôts.'
            ))
            return

        if options['reset_entrepots']:
            n, _ = Entrepot.objects.filter(proprietaire=user).delete()
            if n:
                self.stdout.write(f'{n} ancien(s) entrepôt(s) supprimé(s).')

        img_bytes, img_basename = _seed_image_bytes()

        plans = [
            {
                'titre': 'Box sec Dantokpa — allée A',
                'adresse': 'Marché Dantokpa, allée A, stand 12',
                'ville': Entrepot.Ville.COTONOU,
                'categorie_idx': 0,
                'prix': Decimal('8500.00'),
                'surface': 18,
                'equipements': {'gardien': True, 'camera': True, 'electricite': True, 'zone_frigo': False},
            },
            {
                'titre': 'Chambre froide Akpakpa',
                'adresse': 'Zone industrielle Akpakpa, parcelle 45',
                'ville': Entrepot.Ville.COTONOU,
                'categorie_idx': 1,
                'prix': Decimal('22000.00'),
                'surface': 35,
                'equipements': {'gardien': True, 'camera': True, 'electricite': True, 'zone_frigo': True},
            },
            {
                'titre': 'Garage sécurisé Dantokpa',
                'adresse': 'Dantokpa, rue du commerce, immeuble bleu',
                'ville': Entrepot.Ville.COTONOU,
                'categorie_idx': 2,
                'prix': Decimal('12500.00'),
                'surface': 28,
                'equipements': {'gardien': True, 'camera': False, 'electricite': True, 'alarme': True},
            },
            {
                'titre': 'Local sec Akpakpa — bordure route',
                'adresse': 'Akpakpa, carrefour 3, derrière la station',
                'ville': Entrepot.Ville.COTONOU,
                'categorie_idx': 0,
                'prix': Decimal('5000.00'),
                'surface': 12,
                'equipements': {'gardien': False, 'camera': True, 'electricite': False},
            },
            {
                'titre': 'Entrepôt modulaire Abomey-Calavi',
                'adresse': 'Godomey, près de l’Université d’Abomey-Calavi',
                'ville': Entrepot.Ville.ABOMEY_CALAVI,
                'categorie_idx': 2,
                'prix': Decimal('18500.00'),
                'surface': 42,
                'equipements': {'gardien': True, 'camera': True, 'electricite': True, 'acces_24h': False},
            },
        ]

        for i, plan in enumerate(plans):
            cat = categories[plan['categorie_idx']]
            desc = (
                f"Espace de stockage de démonstration — {plan['titre']}. "
                f"Surface {plan['surface']} m²."
            )
            cf = ContentFile(img_bytes, name=f'seed_entrepot_{i}_{img_basename}')
            e = Entrepot.objects.create(
                proprietaire=user,
                categorie=cat,
                titre=plan['titre'],
                description_detaillee=desc,
                adresse=plan['adresse'],
                ville=plan['ville'],
                image_principale=cf,
                prix_par_jour=plan['prix'],
                surface_m2=plan['surface'],
                equipements=plan['equipements'],
                disponible=True,
            )
            self.stdout.write(self.style.SUCCESS(
                f'Entrepôt créé : {e.titre} ({e.prix_par_jour} FCFA/j)'
            ))
