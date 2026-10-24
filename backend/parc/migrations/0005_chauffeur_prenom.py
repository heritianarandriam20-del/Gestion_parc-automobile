from django.db import migrations, models


def separer_prenom_nom(apps, schema_editor):
    Chauffeur = apps.get_model("parc", "Chauffeur")
    for c in Chauffeur.objects.select_related("user").filter(user__isnull=False):
        if c.user.first_name or c.user.last_name:
            c.prenom = c.user.first_name
            c.nom = c.user.last_name
        elif c.nom == c.user.username:
            c.nom = ""
        c.save()


class Migration(migrations.Migration):

    dependencies = [
        ("parc", "0004_signalement"),
    ]

    operations = [
        migrations.AddField(
            model_name="chauffeur",
            name="prenom",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.AlterField(
            model_name="chauffeur",
            name="nom",
            field=models.CharField(blank=True, max_length=60),
        ),
        migrations.RunPython(separer_prenom_nom, migrations.RunPython.noop),
    ]
