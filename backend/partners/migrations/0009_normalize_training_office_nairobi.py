from django.db import migrations


def normalize_office(apps, schema_editor):
    # Only correct the shorthand explicitly identified by the project owner.
    cohort = apps.get_model('partners', 'TrainingCohort')
    cohort.objects.using(schema_editor.connection.alias).filter(location__iexact='nai').update(location='Nairobi')


class Migration(migrations.Migration):
    dependencies = [('partners', '0008_alter_trainingevent_actor')]
    operations = [migrations.RunPython(normalize_office, migrations.RunPython.noop)]
