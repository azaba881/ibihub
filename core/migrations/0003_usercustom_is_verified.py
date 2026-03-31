from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_categoriestorage_entrepot_reservation'),
    ]

    operations = [
        migrations.AddField(
            model_name='usercustom',
            name='is_verified',
            field=models.BooleanField(
                default=False,
                help_text='Compte vérifié par l’équipe (obligatoire pour publier une annonce).',
            ),
        ),
    ]
