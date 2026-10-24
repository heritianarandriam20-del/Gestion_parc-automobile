import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def clients_vers_chauffeurs(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Chauffeur = apps.get_model("parc", "Chauffeur")
    Reservation = apps.get_model("parc", "Reservation")

    def chauffeur_de(u):
        c = Chauffeur.objects.filter(user=u).first()
        if c is None:
            c = Chauffeur.objects.create(user=u, nom=(f"{u.first_name} {u.last_name}".strip() or u.username)[:60])
        return c

    for u in User.objects.filter(is_superuser=False).exclude(groups__name="Administrateur"):
        chauffeur_de(u)
    for r in Reservation.objects.select_related("client"):
        r.chauffeur = chauffeur_de(r.client)
        r.save(update_fields=["chauffeur"])


class Migration(migrations.Migration):

    dependencies = [
        ("parc", "0002_reservation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="chauffeur",
            name="user",
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="chauffeur", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="chauffeur",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name="reservations", to="parc.chauffeur",
            ),
        ),
        migrations.RunPython(clients_vers_chauffeurs, migrations.RunPython.noop),
        migrations.RemoveField(model_name="reservation", name="client"),
        migrations.AlterField(
            model_name="reservation",
            name="chauffeur",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reservations", to="parc.chauffeur",
            ),
        ),
    ]
