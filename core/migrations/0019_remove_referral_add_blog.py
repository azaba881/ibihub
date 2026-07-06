import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_usercustom_must_set_password'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ParrainageGain',
        ),
        migrations.RemoveField(
            model_name='reservation',
            name='gain_parrainage_verse',
        ),
        migrations.RemoveField(
            model_name='usercustom',
            name='code_parrainage',
        ),
        migrations.RemoveField(
            model_name='usercustom',
            name='parrain',
        ),
        migrations.RemoveField(
            model_name='usercustom',
            name='solde_parrainage',
        ),
        migrations.CreateModel(
            name='ArticleCategorie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=120, unique=True)),
            ],
            options={
                'verbose_name': 'catégorie d’article',
                'verbose_name_plural': 'catégories d’articles',
                'ordering': ['nom'],
            },
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titre', models.CharField(max_length=200)),
                ('slug', models.SlugField(help_text='Nom de lecture (URL), ex. securiser-mon-stockage', max_length=200, unique=True)),
                ('resume', models.CharField(blank=True, help_text='Chapô affiché dans les listes.', max_length=500)),
                ('contenu', models.TextField()),
                ('image_couverture', models.ImageField(blank=True, null=True, upload_to='blog/covers/')),
                ('is_publie', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('auteur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articles_rediges', to=settings.AUTH_USER_MODEL)),
                ('categorie', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='articles', to='core.articlecategorie')),
            ],
            options={
                'verbose_name': 'article',
                'verbose_name_plural': 'articles',
                'ordering': ['-published_at', '-created_at'],
            },
        ),
    ]
