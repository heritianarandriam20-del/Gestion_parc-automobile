from django.contrib import admin

from .models import Affectation, Chauffeur, Entretien, Signalement, Vehicule

admin.site.register(Vehicule)
admin.site.register(Chauffeur)
admin.site.register(Affectation)
admin.site.register(Entretien)
admin.site.register(Signalement)
