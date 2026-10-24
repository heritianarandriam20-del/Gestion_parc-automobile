
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Chauffeur",
            fields=[
                ("numero", models.AutoField(primary_key=True, serialize=False)),
                ("nom", models.CharField(max_length=60)),
                ("telephone", models.CharField(blank=True, max_length=20)),
                ("permis", models.CharField(blank=True, max_length=30)),
            ],
        ),
        migrations.CreateModel(
            name="Vehicule",
            fields=[
                (
                    "immatriculation",
                    models.CharField(max_length=15, primary_key=True, serialize=False),
                ),
                ("marque", models.CharField(max_length=60)),
                ("modele", models.CharField(max_length=60)),
                ("annee", models.IntegerField(default=2020)),
                ("kilometrage", models.IntegerField(default=0)),
                (
                    "statut",
                    models.CharField(
                        choices=[
                            ("disponible", "Disponible"),
                            ("affecte", "Affecté"),
                            ("maintenance", "En maintenance"),
                            ("hors_service", "Hors service"),
                        ],
                        default="disponible",
                        max_length=20,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Entretien",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("type", models.CharField(max_length=60)),
                ("date", models.DateField()),
                ("cout", models.IntegerField(default=0)),
                ("description", models.CharField(blank=True, max_length=200)),
                (
                    "vehicule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entretiens",
                        to="parc.vehicule",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Affectation",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("date_debut", models.DateField()),
                ("date_fin", models.DateField(blank=True, null=True)),
                (
                    "chauffeur",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="affectations",
                        to="parc.chauffeur",
                    ),
                ),
                (
                    "vehicule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="affectations",
                        to="parc.vehicule",
                    ),
                ),
            ],
        ),
    ]
