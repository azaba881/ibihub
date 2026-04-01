from decimal import Decimal

from django.db import migrations, models


def backfill_caution_fields(apps, schema_editor):
    Entrepot = apps.get_model('core', 'Entrepot')
    Reservation = apps.get_model('core', 'Reservation')

    for e in Entrepot.objects.iterator():
        amount = e.montant_caution_fixe or Decimal('0')
        caution_requise = amount > 0
        Entrepot.objects.filter(pk=e.pk).update(caution_requise=caution_requise)

    for r in Reservation.objects.select_related('entrepot').iterator():
        jours = (r.date_fin - r.date_debut).days + 1 if r.date_fin and r.date_debut else 0
        caution = Decimal('0.00')
        if r.entrepot.caution_requise and jours >= 14:
            caution = Decimal(str(r.entrepot.montant_caution_fixe or 0)).quantize(Decimal('0.01'))
        Reservation.objects.filter(pk=r.pk).update(montant_caution=caution)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_kyc_caution_contrat_inventaire'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entrepot',
            old_name='caution_montant_fixe',
            new_name='montant_caution_fixe',
        ),
        migrations.AddField(
            model_name='entrepot',
            name='caution_requise',
            field=models.BooleanField(
                default=False,
                help_text='Active l\'exigence de caution pour les durées longues (>= 14 jours).',
            ),
        ),
        migrations.AlterField(
            model_name='entrepot',
            name='montant_caution_fixe',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Montant fixe de caution si caution_requise est activé et durée >= 14 jours.',
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='caution_rendue',
            field=models.BooleanField(
                default=False,
                help_text='Indique si la caution a été restituée.',
            ),
        ),
        migrations.RunPython(backfill_caution_fields, migrations.RunPython.noop),
    ]
