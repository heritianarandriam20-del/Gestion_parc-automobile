from django.urls import path

from . import views

app_name = "parc"

urlpatterns = [
    path("api/csrf/", views.csrf),
    path("api/connexion/", views.connexion),
    path("api/inscription/", views.inscription),
    path("api/deconnexion/", views.deconnexion),
    path("api/moi/", views.moi),
    path("api/stats/", views.stats),
    path("api/stats-chauffeur/", views.stats_chauffeur),
    path("api/vehicules/", views.vehicules),
    path("api/vehicules/<str:immat>/", views.vehicule_detail),
    path("api/chauffeurs/", views.chauffeurs),
    path("api/chauffeurs/<int:numero>/", views.chauffeur_detail),
    path("api/affectations/", views.affectations),
    path("api/affectations/<int:pk>/", views.affectation_detail),
    path("api/mes-vehicules/", views.mes_vehicules),
    path("api/mes-vehicules/<str:immat>/", views.mon_vehicule_detail),
    path("api/signalements/", views.signalements),
    path("api/signalements/<int:pk>/", views.signalement_detail),
    path("api/entretiens/", views.entretiens),
    path("api/entretiens/<int:pk>/", views.entretien_detail),
]
