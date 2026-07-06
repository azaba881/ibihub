from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_backfill_referral_codes'),
    ]

    operations = [
        migrations.AddField(
            model_name='usercustom',
            name='must_set_password',
            field=models.BooleanField(
                default=False,
                help_text="Bloque l'accès QR/PDF tant que l'utilisateur n'a pas défini son mot de passe.",
            ),
        ),
    ]
