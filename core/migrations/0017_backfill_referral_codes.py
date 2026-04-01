from django.db import migrations


def backfill_referral_codes(apps, schema_editor):
    UserCustom = apps.get_model('core', 'UserCustom')
    for user in UserCustom.objects.filter(code_parrainage__isnull=True):
        code = None
        # Génération simple, collision-safe.
        for _ in range(100):
            candidate = __import__('uuid').uuid4().hex[:8].upper()
            if not UserCustom.objects.filter(code_parrainage=candidate).exists():
                code = candidate
                break
        if not code:
            code = __import__('uuid').uuid4().hex[:8].upper()
        user.code_parrainage = code
        user.save(update_fields=['code_parrainage'])

    for user in UserCustom.objects.filter(code_parrainage=''):
        user.code_parrainage = None
        user.save(update_fields=['code_parrainage'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_favori'),
    ]

    operations = [
        migrations.RunPython(backfill_referral_codes, migrations.RunPython.noop),
    ]
