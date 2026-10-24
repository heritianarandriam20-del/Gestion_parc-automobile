import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("parc", "0003_chauffeur_compte"),
    ]

    operations = [
        migrations.DeleteModel(name="Reservation"),
        migrations.CreateModel(
            name="Signalement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(choices=[("panne", "Panne"), ("reparation", "Demande de réparation")], max_length=20)),
                ("description", models.CharField(max_length=500)),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("en_attente", "En attente"),
                            ("en_cours", "En cours de traitement"),
                            ("traitee", "Traitée"),
                            ("refusee", "Refusée"),
                        ],
                        default="en_attente",
                        max_length=20,
                    ),
                ),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                (
                    "chauffeur",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="signalements", to="parc.chauffeur"
                    ),
                ),
                (
                    "vehicule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="signalements", to="parc.vehicule"
                    ),
                ),
            ],
        ),
    ]
