import json
import re
from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import Affectation, Chauffeur, Entretien, Signalement, Vehicule


@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"ok": True})


def iso(d):
    return d if isinstance(d, str) or d is None else d.isoformat()


def vehicule_dict(v):
    return {
        "immatriculation": v.immatriculation,
        "marque": v.marque,
        "modele": v.modele,
        "annee": v.annee,
        "kilometrage": v.kilometrage,
        "statut": v.statut,
        "statut_libelle": v.get_statut_display(),
    }


def chauffeur_dict(c):
    return {
        "numero": c.numero,
        "prenom": c.prenom,
        "nom": c.nom,
        "nom_complet": c.nom_complet,
        "telephone": c.telephone,
        "permis": c.permis,
        "compte": c.user.username if c.user_id else "",
        "date_inscription": (
            timezone.localtime(c.user.date_joined).date().isoformat() if c.user_id else None
        ),
    }


def affectation_dict(a):
    return {
        "id": a.id,
        "vehicule": a.vehicule_id,
        "vehicule_libelle": f"{a.vehicule.marque} {a.vehicule.modele}",
        "chauffeur": a.chauffeur_id,
        "chauffeur_nom": a.chauffeur.nom_complet,
        "date_debut": iso(a.date_debut),
        "date_fin": iso(a.date_fin),
    }


def entretien_dict(e):
    return {
        "id": e.id,
        "vehicule": e.vehicule_id,
        "vehicule_libelle": f"{e.vehicule.marque} {e.vehicule.modele}",
        "type": e.type,
        "date": iso(e.date),
        "cout": e.cout,
        "description": e.description,
    }


def lire_json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None


def erreur(message, status=400):
    return JsonResponse({"erreur": message}, status=status)


def role_de(user):
    if user.is_superuser or user.groups.filter(name="Administrateur").exists():
        return "admin"
    return "chauffeur"


def chauffeur_de(user):
    c, _ = Chauffeur.objects.get_or_create(
        user=user, defaults={"prenom": user.first_name[:60], "nom": user.last_name[:60]}
    )
    return c


def acces(request, admin=False):
    if not request.user.is_authenticated:
        return erreur("Connexion requise", 401)
    if admin and role_de(request.user) != "admin":
        return erreur("Accès réservé à l'administrateur", 403)
    return None


def lire_date(valeur):
    try:
        return date.fromisoformat(str(valeur))
    except ValueError:
        return None


def verifier_telephone(valeur):
    valeur = str(valeur or "").strip()
    if not valeur:
        return valeur, None
    if not re.fullmatch(r"\+?[0-9 .\-]+", valeur):
        return valeur, "Le téléphone ne doit contenir que des chiffres (espaces, points et tirets autorisés)"
    if len(re.sub(r"\D", "", valeur)) > 15:
        return valeur, "Le numéro de téléphone ne doit pas dépasser 15 chiffres"
    if len(valeur) > 20:
        return valeur, "Le numéro de téléphone est trop long"
    return valeur, None


def verifier_identifiant(username, sauf=None):
    if not username:
        return "L'identifiant est obligatoire"
    if len(username) > 30:
        return "L'identifiant ne doit pas dépasser 30 caractères"
    doublons = User.objects.filter(username__iexact=username)
    if sauf is not None:
        doublons = doublons.exclude(pk=sauf.pk)
    if doublons.exists():
        return "Cet identifiant est déjà utilisé"
    return None


def verifier_mot_de_passe(password, user):
    try:
        validate_password(password, user)
    except ValidationError as e:
        return " ".join(e.messages)
    return None


def creer_chauffeur_avec_compte(data):
    username = str(data.get("username", "")).strip()
    password = data.get("password", "")
    if not username or not password:
        return None, "Identifiant et mot de passe obligatoires"
    if "confirmation" in data and data["confirmation"] != password:
        return None, "Les deux mots de passe ne sont pas identiques"
    message = verifier_identifiant(username)
    if message:
        return None, message
    telephone, message = verifier_telephone(data.get("telephone"))
    if message:
        return None, message
    prenom = str(data.get("prenom", "")).strip()[:30]
    nom = str(data.get("nom", "")).strip()[:30]
    user = User(username=username, first_name=prenom, last_name=nom)
    message = verifier_mot_de_passe(password, user)
    if message:
        return None, message
    user.set_password(password)
    user.save()
    c = Chauffeur.objects.create(
        user=user, prenom=prenom, nom=nom, telephone=telephone, permis=str(data.get("permis", "")).strip()[:30]
    )
    return c, None


def acces_chauffeur(request):
    refus = acces(request)
    if refus:
        return refus
    if role_de(request.user) == "admin":
        return erreur("Accès réservé aux chauffeurs", 403)
    return None


def user_dict(u):
    return {"connecte": True, "username": u.username, "role": role_de(u)}


@require_http_methods(["POST"])
def connexion(request):
    data = lire_json(request) or {}
    user = authenticate(request, username=data.get("username", ""), password=data.get("password", ""))
    if user is None:
        return erreur("Identifiant ou mot de passe incorrect")
    login(request, user)
    return JsonResponse(user_dict(user))


@require_http_methods(["POST"])
def inscription(request):
    data = lire_json(request) or {}
    c, message = creer_chauffeur_avec_compte(data)
    if message:
        return erreur(message)
    login(request, c.user)
    return JsonResponse(user_dict(c.user), status=201)


@require_http_methods(["POST"])
def deconnexion(request):
    logout(request)
    return JsonResponse({"ok": True})


def moi(request):
    if not request.user.is_authenticated:
        return JsonResponse({"connecte": False})
    return JsonResponse(user_dict(request.user))


@require_http_methods(["GET", "POST"])
def vehicules(request):
    refus = acces(request, admin=True)
    if refus:
        return refus
    if request.method == "GET":
        qs = Vehicule.objects.all()
        recherche = request.GET.get("search", "").strip()
        if recherche:
            qs = qs.filter(
                Q(immatriculation__icontains=recherche)
                | Q(marque__icontains=recherche)
                | Q(modele__icontains=recherche)
            )
        statut = request.GET.get("statut", "")
        if statut:
            qs = qs.filter(statut=statut)
        qs = qs.order_by("marque", "modele")
        return JsonResponse([vehicule_dict(v) for v in qs], safe=False)

    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")
    immat = str(data.get("immatriculation", "")).strip().upper()
    if not immat or not data.get("marque") or not data.get("modele"):
        return erreur("Immatriculation, marque et modèle sont obligatoires")
    if Vehicule.objects.filter(pk=immat).exists():
        return erreur("Cette immatriculation existe déjà")
    v = Vehicule.objects.create(
        immatriculation=immat,
        marque=data["marque"].strip(),
        modele=data["modele"].strip(),
        annee=int(data.get("annee") or 2020),
        kilometrage=int(data.get("kilometrage") or 0),
        statut=data.get("statut") or "disponible",
    )
    return JsonResponse(vehicule_dict(v), status=201)


@require_http_methods(["GET", "PUT", "DELETE"])
def vehicule_detail(request, immat):
    refus = acces(request, admin=True)
    if refus:
        return refus
    try:
        v = Vehicule.objects.get(pk=immat)
    except Vehicule.DoesNotExist:
        return erreur("Véhicule introuvable", 404)

    if request.method == "GET":
        d = vehicule_dict(v)
        d["affectations"] = [affectation_dict(a) for a in v.affectations.order_by("-date_debut")]
        d["entretiens"] = [entretien_dict(e) for e in v.entretiens.order_by("-date")]
        return JsonResponse(d)

    if request.method == "DELETE":
        v.delete()
        return JsonResponse({"ok": True})

    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")
    for champ in ("marque", "modele", "statut"):
        if champ in data:
            setattr(v, champ, data[champ])
    for champ in ("annee", "kilometrage"):
        if champ in data and data[champ] != "":
            setattr(v, champ, int(data[champ]))
    v.save()
    return JsonResponse(vehicule_dict(v))


@require_http_methods(["GET", "POST"])
def chauffeurs(request):
    refus = acces(request, admin=True)
    if refus:
        return refus
    if request.method == "GET":
        qs = Chauffeur.objects.select_related("user")
        recherche = request.GET.get("search", "").strip()
        if recherche:
            qs = qs.filter(
                Q(nom__icontains=recherche)
                | Q(prenom__icontains=recherche)
                | Q(permis__icontains=recherche)
                | Q(user__username__icontains=recherche)
            )
        return JsonResponse([chauffeur_dict(c) for c in qs.order_by("nom", "prenom")], safe=False)

    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")
    c, message = creer_chauffeur_avec_compte(data)
    if message:
        return erreur(message)
    return JsonResponse(chauffeur_dict(c), status=201)


@require_http_methods(["PUT", "DELETE"])
def chauffeur_detail(request, numero):
    refus = acces(request, admin=True)
    if refus:
        return refus
    try:
        c = Chauffeur.objects.get(pk=numero)
    except Chauffeur.DoesNotExist:
        return erreur("Chauffeur introuvable", 404)
    if request.method == "DELETE":
        if c.user_id:
            c.user.delete()
        else:
            c.delete()
        return JsonResponse({"ok": True})
    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")

    if "telephone" in data:
        telephone, message = verifier_telephone(data["telephone"])
        if message:
            return erreur(message)
        c.telephone = telephone
    for champ in ("prenom", "nom"):
        if champ in data:
            setattr(c, champ, str(data[champ]).strip()[:30])
    if "permis" in data:
        c.permis = str(data["permis"]).strip()[:30]

    username = str(data.get("username") or "").strip()
    password = data.get("password") or ""
    if password and "confirmation" in data and data["confirmation"] != password:
        return erreur("Les deux mots de passe ne sont pas identiques")
    u = c.user
    if u is not None:
        if username and username != u.username:
            message = verifier_identifiant(username, sauf=u)
            if message:
                return erreur(message)
            u.username = username
        if password:
            message = verifier_mot_de_passe(password, u)
            if message:
                return erreur(message)
            u.set_password(password)
        u.first_name, u.last_name = c.prenom, c.nom
    elif username or password:
        if not (username and password):
            return erreur("Identifiant et mot de passe obligatoires pour créer le compte")
        message = verifier_identifiant(username)
        if message:
            return erreur(message)
        u = User(username=username, first_name=c.prenom, last_name=c.nom)
        message = verifier_mot_de_passe(password, u)
        if message:
            return erreur(message)
        u.set_password(password)

    if u is not None:
        u.save()
        c.user = u
    c.save()
    return JsonResponse(chauffeur_dict(c))


@require_http_methods(["GET", "POST"])
def affectations(request):
    refus = acces(request, admin=True)
    if refus:
        return refus
    if request.method == "GET":
        qs = Affectation.objects.select_related("vehicule", "chauffeur").order_by("-date_debut")
        return JsonResponse([affectation_dict(a) for a in qs], safe=False)

    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")
    try:
        v = Vehicule.objects.get(pk=data.get("vehicule"))
        c = Chauffeur.objects.get(pk=data.get("chauffeur"))
    except (Vehicule.DoesNotExist, Chauffeur.DoesNotExist, ValueError):
        return erreur("Véhicule ou chauffeur invalide")
    debut = lire_date(data.get("date_debut"))
    if debut is None:
        return erreur("La date de début est obligatoire")
    if debut < date.today():
        return erreur("La date de début ne peut pas être dans le passé")
    fin = None
    if data.get("date_fin"):
        fin = lire_date(data["date_fin"])
        if fin is None:
            return erreur("Date de fin invalide")
        if fin < debut:
            return erreur("La date de fin doit être après la date de début")
    if v.statut in ("maintenance", "hors_service"):
        return erreur("Ce véhicule n'est pas disponible (maintenance / hors service)")
    if v.affectations.filter(date_fin__isnull=True).exists():
        return erreur("Ce véhicule a déjà une affectation en cours")
    a = Affectation.objects.create(vehicule=v, chauffeur=c, date_debut=debut, date_fin=fin)
    if a.date_fin is None:
        v.statut = "affecte"
        v.save()
    return JsonResponse(affectation_dict(a), status=201)


@require_http_methods(["PUT", "DELETE"])
def affectation_detail(request, pk):
    refus = acces(request, admin=True)
    if refus:
        return refus
    try:
        a = Affectation.objects.select_related("vehicule", "chauffeur").get(pk=pk)
    except Affectation.DoesNotExist:
        return erreur("Affectation introuvable", 404)
    v = a.vehicule
    if request.method == "DELETE":
        en_cours = a.date_fin is None
        a.delete()
        if en_cours and v.statut == "affecte":
            v.statut = "disponible"
            v.save()
        return JsonResponse({"ok": True})
    if a.date_fin is not None and a.date_fin <= date.today():
        return erreur("Cette affectation est déjà terminée")
    data = lire_json(request) or {}
    a.date_fin = data.get("date_fin") or date.today()
    a.save()
    if v.statut == "affecte":
        v.statut = "disponible"
        v.save()
    return JsonResponse(affectation_dict(a))


@require_http_methods(["GET", "POST"])
def entretiens(request):
    refus = acces(request, admin=True)
    if refus:
        return refus
    if request.method == "GET":
        qs = Entretien.objects.select_related("vehicule").order_by("-date")
        immat = request.GET.get("vehicule")
        if immat:
            qs = qs.filter(vehicule__immatriculation=immat)
        return JsonResponse([entretien_dict(e) for e in qs], safe=False)

    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")
    try:
        v = Vehicule.objects.get(pk=data.get("vehicule"))
    except Vehicule.DoesNotExist:
        return erreur("Véhicule invalide")
    if not data.get("type") or not data.get("date"):
        return erreur("Le type et la date sont obligatoires")
    jour = lire_date(data["date"])
    if jour is None:
        return erreur("Date invalide")
    if jour < date.today():
        return erreur("La date ne peut pas être dans le passé")
    try:
        cout = int(data.get("cout") or 0)
    except (TypeError, ValueError):
        return erreur("Le coût doit être un nombre entier")
    if cout <= 0:
        return erreur("Le coût doit être supérieur à 0 Ar")
    e = Entretien.objects.create(
        vehicule=v,
        type=data["type"],
        date=jour,
        cout=cout,
        description=data.get("description", ""),
    )
    return JsonResponse(entretien_dict(e), status=201)


@require_http_methods(["DELETE"])
def entretien_detail(request, pk):
    refus = acces(request, admin=True)
    if refus:
        return refus
    deleted, _ = Entretien.objects.filter(pk=pk).delete()
    if not deleted:
        return erreur("Entretien introuvable", 404)
    return JsonResponse({"ok": True})


def affectations_en_cours(chauffeur):
    return Affectation.objects.filter(chauffeur=chauffeur).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gt=date.today())
    )


def mon_vehicule_dict(a):
    d = vehicule_dict(a.vehicule)
    d["depuis"] = iso(a.date_debut)
    d["jusqu_au"] = iso(a.date_fin)
    return d


@require_http_methods(["GET"])
def mes_vehicules(request):
    refus = acces_chauffeur(request)
    if refus:
        return refus
    qs = affectations_en_cours(chauffeur_de(request.user)).select_related("vehicule").order_by("vehicule__marque")
    return JsonResponse([mon_vehicule_dict(a) for a in qs], safe=False)


@require_http_methods(["GET"])
def mon_vehicule_detail(request, immat):
    refus = acces_chauffeur(request)
    if refus:
        return refus
    c = chauffeur_de(request.user)
    a = affectations_en_cours(c).select_related("vehicule").filter(vehicule_id=immat).first()
    if a is None:
        return erreur("Ce véhicule ne vous est pas attribué", 404)
    d = mon_vehicule_dict(a)
    d["entretiens"] = [
        {"id": e.id, "type": e.type, "date": iso(e.date), "description": e.description}
        for e in a.vehicule.entretiens.order_by("-date")
    ]
    d["signalements"] = [
        signalement_dict(s)
        for s in Signalement.objects.select_related("chauffeur", "vehicule")
        .filter(chauffeur=c, vehicule=a.vehicule)
        .order_by("-date_creation")
    ]
    return JsonResponse(d)


def signalement_dict(s):
    return {
        "id": s.id,
        "vehicule": s.vehicule_id,
        "vehicule_libelle": f"{s.vehicule.marque} {s.vehicule.modele}",
        "chauffeur": s.chauffeur_id,
        "chauffeur_nom": s.chauffeur.nom_complet,
        "type": s.type,
        "type_libelle": s.get_type_display(),
        "description": s.description,
        "statut": s.statut,
        "statut_libelle": s.get_statut_display(),
        "date": timezone.localtime(s.date_creation).date().isoformat(),
    }


@require_http_methods(["GET", "POST"])
def signalements(request):
    refus = acces(request) if request.method == "GET" else acces_chauffeur(request)
    if refus:
        return refus
    est_admin = role_de(request.user) == "admin"

    if request.method == "GET":
        qs = Signalement.objects.select_related("chauffeur", "vehicule").order_by("-date_creation")
        if not est_admin:
            qs = qs.filter(chauffeur=chauffeur_de(request.user))
        for champ in ("statut", "type"):
            valeur = request.GET.get(champ, "")
            if valeur:
                qs = qs.filter(**{champ: valeur})
        return JsonResponse([signalement_dict(s) for s in qs], safe=False)

    data = lire_json(request)
    if data is None:
        return erreur("JSON invalide")
    c = chauffeur_de(request.user)
    if data.get("type") not in ("panne", "reparation"):
        return erreur("Choisissez le type : panne ou demande de réparation")
    description = str(data.get("description", "")).strip()
    if not description:
        return erreur("Décrivez le problème")
    if len(description) > 500:
        return erreur("La description ne doit pas dépasser 500 caractères")
    v = affectations_en_cours(c).select_related("vehicule").filter(vehicule_id=data.get("vehicule")).first()
    if v is None:
        return erreur("Ce véhicule ne vous est pas attribué")
    s = Signalement.objects.create(chauffeur=c, vehicule=v.vehicule, type=data["type"], description=description)
    return JsonResponse(signalement_dict(s), status=201)


@require_http_methods(["PUT"])
def signalement_detail(request, pk):
    refus = acces(request, admin=True)
    if refus:
        return refus
    try:
        s = Signalement.objects.select_related("chauffeur", "vehicule").get(pk=pk)
    except Signalement.DoesNotExist:
        return erreur("Signalement introuvable", 404)
    data = lire_json(request) or {}
    nouveau = data.get("statut")
    if nouveau not in ("en_cours", "traitee", "refusee"):
        return erreur("Statut invalide")
    if s.statut in ("traitee", "refusee"):
        return erreur("Ce signalement est déjà clôturé")
    if nouveau in ("en_cours", "refusee") and s.statut != "en_attente":
        return erreur("Seul un signalement en attente peut être pris en charge ou refusé")
    s.statut = nouveau
    s.save()
    return JsonResponse(signalement_dict(s))


def stats(request):
    refus = acces(request, admin=True)
    if refus:
        return refus
    total = Vehicule.objects.count()
    par_statut = {code: Vehicule.objects.filter(statut=code).count() for code, _ in Vehicule.STATUTS}
    cout = Entretien.objects.aggregate(t=Sum("cout"))["t"] or 0
    return JsonResponse(
        {
            "total_vehicules": total,
            "par_statut": par_statut,
            "total_chauffeurs": Chauffeur.objects.count(),
            "signalements_en_attente": Signalement.objects.filter(statut="en_attente").count(),
            "cout_entretiens": cout,
            "derniers_entretiens": [
                entretien_dict(e) for e in Entretien.objects.select_related("vehicule").order_by("-date")[:5]
            ],
        }
    )


@require_http_methods(["GET"])
def stats_chauffeur(request):
    refus = acces_chauffeur(request)
    if refus:
        return refus
    c = chauffeur_de(request.user)
    mes = Signalement.objects.select_related("chauffeur", "vehicule").filter(chauffeur=c)
    return JsonResponse(
        {
            "nb_vehicules": affectations_en_cours(c).count(),
            "total_signalements": mes.count(),
            "par_statut": {code: mes.filter(statut=code).count() for code, _ in Signalement.STATUTS},
            "nb_pannes": mes.filter(type="panne").count(),
            "nb_reparations": mes.filter(type="reparation").count(),
            "vehicules": [
                mon_vehicule_dict(a)
                for a in affectations_en_cours(c).select_related("vehicule").order_by("vehicule__marque")
            ],
            "derniers_signalements": [signalement_dict(x) for x in mes.order_by("-date_creation")[:5]],
        }
    )
