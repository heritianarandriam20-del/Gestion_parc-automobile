import json
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase

from .models import Affectation, Chauffeur, Signalement, Vehicule


class ApiParcTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss", "", "x"))

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def test_csrf_cookie(self):
        r = self.client.get("/api/csrf/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("csrftoken", r.cookies)

    def test_creation_et_recherche_vehicule(self):
        r = self.post("/api/vehicules/", {"immatriculation": "1234 TAA", "marque": "Toyota", "modele": "Hilux"})
        self.assertEqual(r.status_code, 201)
        self.post("/api/vehicules/", {"immatriculation": "5678 TBB", "marque": "Renault", "modele": "Duster"})
        r = self.client.get("/api/vehicules/?search=toy")
        self.assertEqual([v["marque"] for v in r.json()], ["Toyota"])
        r = self.post("/api/vehicules/", {"immatriculation": "1234 TAA", "marque": "X", "modele": "Y"})
        self.assertEqual(r.status_code, 400)

    def test_affectation_change_statut(self):
        Vehicule.objects.create(immatriculation="A1", marque="Kia", modele="Rio")
        c = Chauffeur.objects.create(nom="Rakoto")
        r = self.post("/api/affectations/", {"vehicule": "A1", "chauffeur": c.numero, "date_debut": str(date.today())})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Vehicule.objects.get(pk="A1").statut, "affecte")
        r = self.post("/api/affectations/", {"vehicule": "A1", "chauffeur": c.numero, "date_debut": str(date.today())})
        self.assertEqual(r.status_code, 400)
        a_id = r.json and self.client.get("/api/affectations/").json()[0]["id"]
        r = self.client.put(f"/api/affectations/{a_id}/", "{}", content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Vehicule.objects.get(pk="A1").statut, "disponible")

    def test_entretien_et_stats(self):
        Vehicule.objects.create(immatriculation="B2", marque="Ford", modele="Ranger")
        r = self.post("/api/entretiens/", {"vehicule": "B2", "type": "Vidange", "date": str(date.today()), "cout": 150000})
        self.assertEqual(r.status_code, 201)
        s = self.client.get("/api/stats/").json()
        self.assertEqual(s["cout_entretiens"], 150000)
        self.assertEqual(s["total_vehicules"], 1)


class ValidationsAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss", "", "x"))
        Vehicule.objects.create(immatriculation="K1", marque="Kia", modele="Rio")
        self.chauffeur = Chauffeur.objects.create(nom="Rakoto")
        self.hier = date.today() - timedelta(days=1)
        self.demain = date.today() + timedelta(days=1)

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def entretien(self, **extra):
        data = {"vehicule": "K1", "type": "Vidange", "date": str(date.today()), "cout": 50000}
        data.update(extra)
        return self.post("/api/entretiens/", data)

    def affectation(self, **extra):
        data = {"vehicule": "K1", "chauffeur": self.chauffeur.numero, "date_debut": str(date.today())}
        data.update(extra)
        return self.post("/api/affectations/", data)

    def test_entretien_date_passee_refusee(self):
        r = self.entretien(date=str(self.hier))
        self.assertEqual(r.status_code, 400)
        self.assertIn("passé", r.json()["erreur"])
        self.assertEqual(self.entretien(date=str(self.demain)).status_code, 201)
        self.assertEqual(self.entretien(date="pas-une-date").status_code, 400)

    def test_entretien_cout_zero_refuse(self):
        for cout in (0, "0", "", None, -5, "abc"):
            self.assertEqual(self.entretien(cout=cout).status_code, 400, cout)
        r = self.entretien(cout=0)
        self.assertIn("supérieur à 0", r.json()["erreur"])
        self.assertEqual(self.entretien(cout=1).status_code, 201)

    def test_affectation_date_passee_refusee(self):
        r = self.affectation(date_debut=str(self.hier))
        self.assertEqual(r.status_code, 400)
        self.assertIn("passé", r.json()["erreur"])
        self.assertEqual(self.affectation(date_fin=str(self.hier)).status_code, 400)
        self.assertEqual(self.affectation().status_code, 201)

    def test_telephone_15_chiffres_maximum(self):
        base = {"username": "t1", "password": "MotDePasse2026!"}
        ok = self.post("/api/chauffeurs/", {**base, "telephone": "123456789012345"})
        self.assertEqual(ok.status_code, 201)
        trop = self.post("/api/chauffeurs/", {**base, "username": "t2", "telephone": "1234567890123456"})
        self.assertEqual(trop.status_code, 400)
        self.assertIn("15 chiffres", trop.json()["erreur"])
        lettres = self.post("/api/chauffeurs/", {**base, "username": "t3", "telephone": "03412abc"})
        self.assertEqual(lettres.status_code, 400)
        formate = self.post("/api/chauffeurs/", {**base, "username": "t4", "telephone": "+261 34 12 345 67"})
        self.assertEqual(formate.status_code, 201)

    def test_telephone_modification(self):
        c = self.post("/api/chauffeurs/", {"username": "t5", "password": "MotDePasse2026!"}).json()
        r = self.client.put(f"/api/chauffeurs/{c['numero']}/", json.dumps({"telephone": "1" * 16}), content_type="application/json")
        self.assertEqual(r.status_code, 400)


class AdminChauffeursTests(TestCase):

    def setUp(self):
        self.client.force_login(User.objects.create_superuser("boss", "", "x"))

    def post(self, data):
        return self.client.post("/api/chauffeurs/", json.dumps(data), content_type="application/json")

    def put(self, numero, data):
        return self.client.put(f"/api/chauffeurs/{numero}/", json.dumps(data), content_type="application/json")

    def complet(self, **extra):
        data = {"username": "marie", "prenom": "Marie", "nom": "Rasoa", "telephone": "034 00 000 00",
                "permis": "P123", "password": "MotDePasse2026!", "confirmation": "MotDePasse2026!"}
        data.update(extra)
        return data

    def test_creation_avec_compte_et_connexion_possible(self):
        r = self.post(self.complet())
        self.assertEqual(r.status_code, 201)
        d = r.json()
        self.assertEqual((d["prenom"], d["nom"], d["nom_complet"], d["compte"]), ("Marie", "Rasoa", "Marie Rasoa", "marie"))
        u = User.objects.get(username="marie")
        self.assertFalse(u.is_superuser or u.is_staff)
        from django.test import Client
        r = Client().post("/api/connexion/", json.dumps({"username": "marie", "password": "MotDePasse2026!"}), content_type="application/json")
        self.assertEqual(r.json()["role"], "chauffeur")

    def test_memes_regles_que_l_inscription(self):
        self.assertEqual(self.post(self.complet(password="123", confirmation="123")).status_code, 400)
        self.assertEqual(self.post(self.complet(confirmation="Autre2026!")).status_code, 400)
        self.assertEqual(self.post(self.complet(username="")).status_code, 400)
        self.assertEqual(self.post(self.complet()).status_code, 201)
        self.assertEqual(self.post(self.complet(username="MARIE")).status_code, 400)

    def test_modifier_tous_les_champs(self):
        numero = self.post(self.complet()).json()["numero"]
        r = self.put(numero, {"username": "marie2", "prenom": "Marie-Jeanne", "nom": "Rabe", "telephone": "0341234567",
                              "permis": "Z9", "password": "NouveauMdp2026!", "confirmation": "NouveauMdp2026!"})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual((d["compte"], d["nom_complet"], d["telephone"], d["permis"]),
                         ("marie2", "Marie-Jeanne Rabe", "0341234567", "Z9"))
        u = User.objects.get(username="marie2")
        self.assertEqual((u.first_name, u.last_name), ("Marie-Jeanne", "Rabe"))
        self.assertTrue(u.check_password("NouveauMdp2026!"))

    def test_mot_de_passe_vide_ne_change_rien(self):
        numero = self.post(self.complet()).json()["numero"]
        self.put(numero, {"nom": "Rabe", "password": "", "confirmation": ""})
        self.assertTrue(User.objects.get(username="marie").check_password("MotDePasse2026!"))

    def test_identifiant_deja_pris_en_modification(self):
        self.post(self.complet(username="paul"))
        numero = self.post(self.complet()).json()["numero"]
        self.assertEqual(self.put(numero, {"username": "paul"}).status_code, 400)
        self.assertEqual(self.put(numero, {"username": "marie"}).status_code, 200)

    def test_donner_un_compte_a_un_ancien_chauffeur(self):
        ancien = Chauffeur.objects.create(nom="Rakoto")
        self.assertEqual(self.put(ancien.numero, {"username": "rakoto"}).status_code, 400)
        r = self.put(ancien.numero, {"username": "rakoto", "password": "MotDePasse2026!"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["compte"], "rakoto")


class RolesTests(TestCase):
    def test_sans_connexion(self):
        self.assertEqual(self.client.get("/api/vehicules/").status_code, 401)
        self.assertEqual(self.client.get("/api/moi/").json(), {"connecte": False})

    def test_connexion_et_mauvais_mot_de_passe(self):
        User.objects.create_user("bob", "", "secret")
        r = self.client.post("/api/connexion/", json.dumps({"username": "bob", "password": "faux"}), content_type="application/json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/connexion/", json.dumps({"username": "bob", "password": "secret"}), content_type="application/json")
        self.assertEqual(r.json()["role"], "chauffeur")

    def test_chauffeur_lecture_seule(self):
        Vehicule.objects.create(immatriculation="C1", marque="Kia", modele="Rio")
        self.client.force_login(User.objects.create_user("cli", "", "x"))
        r = self.client.post("/api/vehicules/", json.dumps({"immatriculation": "C2", "marque": "A", "modele": "B"}), content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.delete("/api/vehicules/C1/").status_code, 403)
        for url in ("/api/vehicules/", "/api/vehicules/C1/", "/api/stats/", "/api/chauffeurs/", "/api/affectations/", "/api/entretiens/"):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_groupe_administrateur(self):
        u = User.objects.create_user("chef", "", "x")
        u.groups.add(Group.objects.create(name="Administrateur"))
        self.client.force_login(u)
        self.assertEqual(self.client.get("/api/stats/").status_code, 200)


class InscriptionTests(TestCase):
    def post(self, data):
        return self.client.post("/api/inscription/", json.dumps(data), content_type="application/json")

    def test_inscription_cree_un_chauffeur_connecte(self):
        r = self.post({"username": "marie", "password": "MotDePasse2026!", "prenom": "Marie", "nom": "Rasoa"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["role"], "chauffeur")
        u = User.objects.get(username="marie")
        self.assertFalse(u.is_superuser or u.is_staff)
        self.assertEqual(self.client.get("/api/mes-vehicules/").status_code, 200)
        self.assertEqual(self.client.get("/api/stats/").status_code, 403)

    def test_identifiant_deja_pris(self):
        User.objects.create_user("marie", "", "x")
        r = self.post({"username": "Marie", "password": "MotDePasse2026!"})
        self.assertEqual(r.status_code, 400)

    def test_mot_de_passe_trop_simple(self):
        for faible in ("123", "12345678", "password"):
            self.assertEqual(self.post({"username": "u" + faible, "password": faible}).status_code, 400, faible)

    def test_impossible_de_se_faire_administrateur(self):
        r = self.post({"username": "pirate", "password": "MotDePasse2026!", "is_superuser": True, "is_staff": True, "role": "admin"})
        self.assertEqual(r.json()["role"], "chauffeur")
        self.assertFalse(User.objects.get(username="pirate").is_superuser)


class VehiculesDuChauffeurTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "", "x")
        self.marie = User.objects.create_user("marie", "", "x")
        self.paul = User.objects.create_user("paul", "", "x")
        self.cm = Chauffeur.objects.create(user=self.marie, nom="Marie")
        self.cp = Chauffeur.objects.create(user=self.paul, nom="Paul")
        self.v1 = Vehicule.objects.create(immatriculation="V1", marque="Kia", modele="Rio", kilometrage=1000)
        self.v2 = Vehicule.objects.create(immatriculation="V2", marque="Ford", modele="Ranger")
        Affectation.objects.create(vehicule=self.v1, chauffeur=self.cm, date_debut="2026-01-01")
        Affectation.objects.create(vehicule=self.v2, chauffeur=self.cp, date_debut="2026-01-01")

    def poster(self, data):
        return self.client.post("/api/signalements/", json.dumps(data), content_type="application/json")

    def changer(self, pk, statut):
        return self.client.put(f"/api/signalements/{pk}/", json.dumps({"statut": statut}), content_type="application/json")

    def test_le_chauffeur_ne_voit_que_ses_vehicules(self):
        self.client.force_login(self.marie)
        r = self.client.get("/api/mes-vehicules/").json()
        self.assertEqual([v["immatriculation"] for v in r], ["V1"])
        self.assertEqual(r[0]["depuis"], "2026-01-01")

    def test_affectation_terminee_n_est_plus_visible(self):
        Affectation.objects.filter(chauffeur=self.cm).update(date_fin="2020-01-01")
        self.client.force_login(self.marie)
        self.assertEqual(self.client.get("/api/mes-vehicules/").json(), [])

    def test_terminer_l_affectation_vide_l_espace_du_chauffeur(self):
        Affectation.objects.filter(chauffeur=self.cm).delete()
        a = Affectation.objects.create(vehicule=self.v1, chauffeur=self.cm, date_debut=date.today())
        self.client.force_login(self.marie)
        self.assertEqual(len(self.client.get("/api/mes-vehicules/").json()), 1)
        self.assertEqual(self.client.get("/api/stats-chauffeur/").json()["nb_vehicules"], 1)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.put(f"/api/affectations/{a.id}/", "{}", content_type="application/json").status_code, 200)
        self.client.force_login(self.marie)
        self.assertEqual(self.client.get("/api/mes-vehicules/").json(), [])
        self.assertEqual(self.client.get("/api/mes-vehicules/V1/").status_code, 404)
        stats = self.client.get("/api/stats-chauffeur/").json()
        self.assertEqual((stats["nb_vehicules"], stats["vehicules"]), (0, []))
        self.assertEqual(self.poster({"vehicule": "V1", "type": "panne", "description": "x"}).status_code, 400)

    def test_terminer_deux_fois_refuse(self):
        a = Affectation.objects.create(vehicule=self.v1, chauffeur=self.cm, date_debut=date.today())
        self.client.force_login(self.admin)
        self.client.put(f"/api/affectations/{a.id}/", "{}", content_type="application/json")
        r = self.client.put(f"/api/affectations/{a.id}/", "{}", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_fin_prevue_demain_encore_visible_aujourd_hui_non_apres(self):
        Affectation.objects.filter(chauffeur=self.cm).update(date_fin=date.today() + timedelta(days=1))
        self.client.force_login(self.marie)
        self.assertEqual(len(self.client.get("/api/mes-vehicules/").json()), 1)
        Affectation.objects.filter(chauffeur=self.cm).update(date_fin=date.today())
        self.assertEqual(self.client.get("/api/mes-vehicules/").json(), [])

    def test_detail_vehicule_et_historique_entretien(self):
        from .models import Entretien
        Entretien.objects.create(vehicule=self.v1, type="Vidange", date="2026-03-01", cout=150000)
        self.client.force_login(self.marie)
        d = self.client.get("/api/mes-vehicules/V1/").json()
        self.assertEqual(d["kilometrage"], 1000)
        self.assertEqual(d["entretiens"][0]["type"], "Vidange")
        self.assertNotIn("cout", d["entretiens"][0])
        self.assertEqual(self.client.get("/api/mes-vehicules/V2/").status_code, 404)

    def test_signaler_une_panne_et_demander_une_reparation(self):
        self.client.force_login(self.marie)
        r = self.poster({"vehicule": "V1", "type": "panne", "description": "Moteur qui chauffe"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["statut"], "en_attente")
        r = self.poster({"vehicule": "V1", "type": "reparation", "description": "Changer les freins"})
        self.assertEqual(r.status_code, 201)
        d = self.client.get("/api/mes-vehicules/V1/").json()
        self.assertEqual(len(d["signalements"]), 2)

    def test_signalement_invalide(self):
        self.client.force_login(self.marie)
        self.assertEqual(self.poster({"vehicule": "V2", "type": "panne", "description": "x"}).status_code, 400)
        self.assertEqual(self.poster({"vehicule": "V1", "type": "autre", "description": "x"}).status_code, 400)
        self.assertEqual(self.poster({"vehicule": "V1", "type": "panne", "description": "  "}).status_code, 400)
        self.assertEqual(Signalement.objects.count(), 0)

    def test_confidentialite_entre_chauffeurs(self):
        self.client.force_login(self.marie)
        self.poster({"vehicule": "V1", "type": "panne", "description": "Pneu crevé"})
        self.client.force_login(self.paul)
        self.assertEqual(self.client.get("/api/signalements/").json(), [])
        self.client.force_login(self.admin)
        self.assertEqual(len(self.client.get("/api/signalements/").json()), 1)

    def test_admin_traite_le_signalement(self):
        self.client.force_login(self.marie)
        sid = self.poster({"vehicule": "V1", "type": "panne", "description": "Batterie"}).json()["id"]
        self.assertEqual(self.changer(sid, "traitee").status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.changer(sid, "en_cours").json()["statut"], "en_cours")
        self.assertEqual(self.changer(sid, "refusee").status_code, 400)
        self.assertEqual(self.changer(sid, "traitee").json()["statut"], "traitee")
        self.assertEqual(self.changer(sid, "en_cours").status_code, 400)
        self.client.force_login(self.marie)
        self.assertEqual(self.client.get("/api/signalements/").json()[0]["statut"], "traitee")

    def test_admin_ne_peut_pas_signaler(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.poster({"vehicule": "V1", "type": "panne", "description": "x"}).status_code, 403)
        self.assertEqual(self.client.get("/api/mes-vehicules/").status_code, 403)

    def test_sans_connexion(self):
        for url in ("/api/mes-vehicules/", "/api/mes-vehicules/V1/", "/api/signalements/", "/api/stats-chauffeur/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)


class ChauffeursEtTableauDeBordTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("boss", "", "x")

    def inscrire(self, username, **extra):
        from django.test import Client
        data = {"username": username, "password": "MotDePasse2026!", "prenom": "Marie", "nom": "Rasoa"}
        data.update(extra)
        return Client().post("/api/inscription/", json.dumps(data), content_type="application/json")

    def test_compte_cree_cote_chauffeur_visible_cote_admin(self):
        r = self.inscrire("marie", telephone="034 00 000 00", permis="P123")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["role"], "chauffeur")
        self.client.force_login(self.admin)
        liste = self.client.get("/api/chauffeurs/").json()
        self.assertEqual(len(liste), 1)
        self.assertEqual(liste[0]["compte"], "marie")
        self.assertEqual(liste[0]["nom_complet"], "Marie Rasoa")
        self.assertEqual((liste[0]["prenom"], liste[0]["nom"]), ("Marie", "Rasoa"))
        self.assertEqual(liste[0]["telephone"], "034 00 000 00")
        self.assertEqual(liste[0]["permis"], "P123")
        self.assertEqual(self.client.get("/api/stats/").json()["total_chauffeurs"], 1)

    def test_recherche_par_identifiant(self):
        self.inscrire("marie")
        self.inscrire("paul", prenom="Paul", nom="Rabe")
        self.client.force_login(self.admin)
        r = self.client.get("/api/chauffeurs/?search=pau").json()
        self.assertEqual([c["compte"] for c in r], ["paul"])

    def test_chauffeur_cree_par_admin_a_un_compte(self):
        self.client.force_login(self.admin)
        r = self.client.post("/api/chauffeurs/", json.dumps({"username": "rakoto", "password": "MotDePasse2026!"}), content_type="application/json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get("/api/chauffeurs/").json()[0]["compte"], "rakoto")

    def test_supprimer_chauffeur_supprime_son_compte(self):
        self.inscrire("marie")
        numero = Chauffeur.objects.get(user__username="marie").numero
        self.client.force_login(self.admin)
        self.assertEqual(self.client.delete(f"/api/chauffeurs/{numero}/").status_code, 200)
        self.assertFalse(User.objects.filter(username="marie").exists())

    def test_liste_chauffeurs_reservee_a_l_admin(self):
        self.assertEqual(self.client.get("/api/chauffeurs/").status_code, 401)
        self.client.force_login(User.objects.create_user("cli", "", "x"))
        self.assertEqual(self.client.get("/api/chauffeurs/").status_code, 403)

    def test_tableau_de_bord_chauffeur(self):
        v = Vehicule.objects.create(immatriculation="D1", marque="Kia", modele="Rio")
        marie = User.objects.create_user("marie", "", "x")
        paul = User.objects.create_user("paul", "", "x")
        cm = Chauffeur.objects.create(user=marie, nom="Marie")
        cp = Chauffeur.objects.create(user=paul, nom="Paul")
        Affectation.objects.create(vehicule=v, chauffeur=cm, date_debut="2026-01-01")
        Signalement.objects.create(chauffeur=cm, vehicule=v, type="panne", description="a")
        Signalement.objects.create(chauffeur=cm, vehicule=v, type="reparation", description="b", statut="traitee")
        Signalement.objects.create(chauffeur=cp, vehicule=v, type="panne", description="c")
        self.client.force_login(marie)
        s = self.client.get("/api/stats-chauffeur/").json()
        self.assertEqual(s["nb_vehicules"], 1)
        self.assertEqual(s["total_signalements"], 2)
        self.assertEqual(s["par_statut"]["en_attente"], 1)
        self.assertEqual(s["par_statut"]["traitee"], 1)
        self.assertEqual(s["nb_pannes"], 1)
        self.assertEqual(s["nb_reparations"], 1)
        self.assertEqual(s["vehicules"][0]["immatriculation"], "D1")

    def test_stats_admin_compte_les_signalements_en_attente(self):
        v = Vehicule.objects.create(immatriculation="D2", marque="Kia", modele="Rio")
        c = Chauffeur.objects.create(nom="Rakoto")
        Signalement.objects.create(chauffeur=c, vehicule=v, type="panne", description="a")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/api/stats/").json()["signalements_en_attente"], 1)

    def test_tableau_de_bord_chauffeur_connexion_requise(self):
        self.assertEqual(self.client.get("/api/stats-chauffeur/").status_code, 401)

    def test_compte_cree_dans_admin_django_a_une_fiche_chauffeur(self):
        marie = User.objects.create_user("marie", "", "x")
        self.client.force_login(marie)
        self.assertEqual(self.client.get("/api/stats-chauffeur/").status_code, 200)
        self.assertTrue(Chauffeur.objects.filter(user=marie).exists())
