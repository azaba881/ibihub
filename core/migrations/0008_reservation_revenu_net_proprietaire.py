# Generated manually — revenu net propriétaire persisté + backfill

from decimal import Decimal

from django.db import migrations, models


def backfill_revenu_net(apps, schema_editor):
    Reservation = apps.get_model('core', 'Reservation')
    for r in Reservation.objects.iterator():
        mt = r.montant_total or Decimal('0')
        fa = r.frais_assurance or Decimal('0')
        net = (Decimal(str(mt)) - Decimal(str(fa))).quantize(Decimal('0.01'))
        Reservation.objects.filter(pk=r.pk).update(revenu_net_proprietaire=net)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_entrepot_periode_bloquee'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='revenu_net_proprietaire',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                editable=False,
                help_text='Net propriétaire après commission (recalculé à chaque enregistrement).',
                max_digits=12,
            ),
        ),
        migrations.RunPython(backfill_revenu_net, migrations.RunPython.noop),
    ]
