# Generated manually for EntrepotPeriodeBloquee

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_entrepot_avis'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntrepotPeriodeBloquee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_debut', models.DateField()),
                ('date_fin', models.DateField()),
                ('motif', models.CharField(blank=True, max_length=255)),
                (
                    'entrepot',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='periodes_bloquees',
                        to='core.entrepot',
                    ),
                ),
            ],
            options={
                'verbose_name': 'période bloquée',
                'verbose_name_plural': 'périodes bloquées',
                'ordering': ['date_debut'],
            },
        ),
    ]
