from django.conf import settings
from django.db import models


class Vehicule(models.Model):
    STATUTS = [
        ("disponible", "Disponible"),
        ("affecte", "Affecté"),
        ("maintenance", "En maintenance"),
        ("hors_service", "Hors service"),
    ]
    immatriculation = models.CharField(max_length=15, primary_key=True)
    marque = models.CharField(max_length=60)
    modele = models.CharField(max_length=60)
    annee = models.IntegerField(default=2020)
    kilometrage = models.IntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUTS, default="disponible")

    def __str__(self):
        return f"{self.immatriculation} - {self.marque} {self.modele}"


class Chauffeur(models.Model):
    numero = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="chauffeur"
    )
    prenom = models.CharField(max_length=60, blank=True)
    nom = models.CharField(max_length=60, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    permis = models.CharField(max_length=30, blank=True)

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip() or (self.user.username if self.user_id else "")

    def __str__(self):
        return self.nom_complet


class Affectation(models.Model):
    id = models.AutoField(primary_key=True)
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name="affectations")
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.CASCADE, related_name="affectations")
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.vehicule_id} -> {self.chauffeur.nom}"


class Entretien(models.Model):
    id = models.AutoField(primary_key=True)
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name="entretiens")
    type = models.CharField(max_length=60)
    date = models.DateField()
    cout = models.IntegerField(default=0)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.vehicule_id} - {self.type}"


class Signalement(models.Model):
    TYPES = [
        ("panne", "Panne"),
        ("reparation", "Demande de réparation"),
    ]
    STATUTS = [
        ("en_attente", "En attente"),
        ("en_cours", "En cours de traitement"),
        ("traitee", "Traitée"),
        ("refusee", "Refusée"),
    ]
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.CASCADE, related_name="signalements")
    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name="signalements")
    type = models.CharField(max_length=20, choices=TYPES)
    description = models.CharField(max_length=500)
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_attente")
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.vehicule_id} ({self.statut})"
