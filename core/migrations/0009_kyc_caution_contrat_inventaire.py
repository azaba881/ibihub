# KYC utilisateur, caution entrepôt, inventaire / caution / PDF réservation

from decimal import Decimal

from django.db import migrations, models


def backfill_montant_caution(apps, schema_editor):
    from django.conf import settings as dj_settings

    Reservation = apps.get_model('core', 'Reservation')
    rate = getattr(dj_settings, 'IBIHUB_CAUTION_RATE', Decimal('0.20'))
    rate = Decimal(str(rate))
    for r in Reservation.objects.select_related('entrepot').iterator():
        fixe = getattr(r.entrepot, 'caution_montant_fixe', None)
        mt = r.montant_total or Decimal('0')
        if fixe is not None and fixe > 0:
            mc = Decimal(str(fixe)).quantize(Decimal('0.01'))
        else:
            mc = (Decimal(str(mt)) * rate).quantize(Decimal('0.01'))
        Reservation.objects.filter(pk=r.pk).update(montant_caution=mc)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_reservation_revenu_net_proprietaire'),
    ]

    operations = [
        migrations.AddField(
            model_name='usercustom',
            name='piece_identite',
            field=models.ImageField(
                blank=True,
                help_text='Scan ou photo de la pièce (traitement par l’équipe IbiHub).',
                null=True,
                upload_to='kyc/',
            ),
        ),
        migrations.AddField(
            model_name='usercustom',
            name='type_piece',
            field=models.CharField(
                blank=True,
                choices=[('CIP', 'CIP'), ('CNI', 'CNI'), ('PASSEPORT', 'Passeport')],
                help_text='Type de pièce d’identité transmise pour vérification.',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='entrepot',
            name='caution_montant_fixe',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Si renseigné, sert de caution pour toute réservation sur cet espace. Sinon : 20 % du loyer.',
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='contrat_pdf',
            field=models.FileField(
                blank=True,
                help_text='Contrat de bail généré à la confirmation.',
                null=True,
                upload_to='reservations/contrats/',
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='inventaire_depot',
            field=models.TextField(
                blank=True,
                help_text='Liste des marchandises déclarée par le locataire.',
            ),
        ),
        migrations.AddField(
            model_name='reservation',
            name='montant_caution',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                editable=False,
                help_text='Caution : montant fixe de l’entrepôt ou pourcentage du loyer (settings).',
                max_digits=12,
            ),
        ),
        migrations.RunPython(backfill_montant_caution, migrations.RunPython.noop),
    ]
