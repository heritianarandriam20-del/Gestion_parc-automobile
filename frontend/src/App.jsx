import { useState, useEffect } from "react";

function lireCookie(nom) {
  const trouve = document.cookie.split("; ").find((c) => c.startsWith(nom + "="));
  return trouve ? decodeURIComponent(trouve.split("=")[1]) : "";
}

async function api(url, methode = "GET", donnees = null) {
  const options = {
    method: methode,
    headers: { "Content-Type": "application/json", "X-CSRFToken": lireCookie("csrftoken") },
  };
  if (donnees !== null) options.body = JSON.stringify(donnees);
  const reponse = await fetch(url, options);
  const corps = await reponse.json().catch(() => ({}));
  if (!reponse.ok) {
    if (corps.erreur) throw new Error(corps.erreur);
    throw new Error(
      "Erreur " + reponse.status + " sur " + url +
      " : vérifiez que le serveur Django de ce projet est lancé (py manage.py runserver dans backend/)"
    );
  }
  return corps;
}

function aujourdhui() {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

const PROPS_TEL = {
  type: "tel",
  inputMode: "tel",
  maxLength: 20,
  pattern: "(?=(?:\\D*\\d){0,15}\\D*$)\\+?[0-9 .\\-]*",
  title: "Chiffres uniquement, 15 chiffres au maximum",
};

const formaterMontant = (n) => Number(n).toLocaleString("fr-FR") + " Ar";

function formaterDate(iso) {
  if (!iso) return "—";
  const [a, m, j] = iso.split("-");
  return j + "/" + m + "/" + a;
}

const LIBELLES_STATUT = {
  disponible: "Disponible",
  affecte: "Affecté",
  maintenance: "En maintenance",
  hors_service: "Hors service",
};

function Message({ type, texte }) {
  if (!texte) return null;
  return <div className={"message " + type}>{texte}</div>;
}

function Badge({ statut, libelle }) {
  return <span className={"badge " + statut}>{libelle || LIBELLES_STATUT[statut] || statut}</span>;
}

function Champ({ label, children }) {
  return (
    <label>
      {label}
      {children}
    </label>
  );
}

function useListe(url) {
  const [donnees, setDonnees] = useState([]);
  const [erreur, setErreur] = useState("");

  function recharger() {
    api(url)
      .then((d) => {
        setDonnees(d);
        setErreur("");
      })
      .catch((e) => setErreur(e.message));
  }

  useEffect(recharger, [url]);
  return [donnees, recharger, erreur];
}

const PAR_PAGE = 5;

function usePagination(liste, reinit = "") {
  const [page, setPage] = useState(1);
  const nbPages = Math.max(1, Math.ceil(liste.length / PAR_PAGE));
  useEffect(() => setPage(1), [reinit]);
  const courante = Math.min(page, nbPages);
  const visibles = liste.slice((courante - 1) * PAR_PAGE, courante * PAR_PAGE);
  return { visibles, page: courante, nbPages, total: liste.length, aller: setPage };
}

function Pagination({ p }) {
  if (p.total <= PAR_PAGE) return null;
  const debut = (p.page - 1) * PAR_PAGE + 1;
  const fin = Math.min(p.page * PAR_PAGE, p.total);
  return (
    <div className="pagination">
      <span className="info">{debut}–{fin} sur {p.total}</span>
      <div className="boutons">
        <button className="btn sec petit" disabled={p.page === 1} onClick={() => p.aller(p.page - 1)}>Précédent</button>
        {Array.from({ length: p.nbPages }, (_, i) => i + 1).map((n) => (
          <button key={n} className={"btn petit " + (n === p.page ? "" : "sec")} onClick={() => p.aller(n)}>{n}</button>
        ))}
        <button className="btn sec petit" disabled={p.page === p.nbPages} onClick={() => p.aller(p.page + 1)}>Suivant</button>
      </div>
    </div>
  );
}

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    api("/api/stats/").then(setStats).catch((e) => setErreur(e.message));
  }, []);

  if (erreur) return <Message type="erreur" texte={erreur} />;
  if (!stats) return <p>Chargement…</p>;

  const cartes = [
    { libelle: "Véhicules", valeur: stats.total_vehicules, classe: "" },
    { libelle: "Disponibles", valeur: stats.par_statut.disponible, classe: "" },
    { libelle: "Affectés", valeur: stats.par_statut.affecte, classe: "" },
    { libelle: "En maintenance", valeur: stats.par_statut.maintenance, classe: "" },
    { libelle: "Hors service", valeur: stats.par_statut.hors_service, classe: "" },
    { libelle: "Chauffeurs", valeur: stats.total_chauffeurs, classe: "" },
    { libelle: "Pannes / réparations en attente", valeur: stats.signalements_en_attente, classe: "" },
    { libelle: "Coût des entretiens", valeur: formaterMontant(stats.cout_entretiens), classe: "" },
  ];

  return (
    <>
      <div className="grille">
        {cartes.map((c) => (
          <div className={"stat " + c.classe} key={c.libelle}>
            <div className="valeur">{c.valeur}</div>
            <div className="libelle">{c.libelle}</div>
          </div>
        ))}
      </div>

      <div className="carte">
        <h2>Derniers entretiens</h2>
        <table>
          <thead>
            <tr><th>Date</th><th>Véhicule</th><th>Type</th><th>Coût</th></tr>
          </thead>
          <tbody>
            {stats.derniers_entretiens.map((e) => (
              <tr key={e.id}>
                <td>{formaterDate(e.date)}</td>
                <td>{e.vehicule} — {e.vehicule_libelle}</td>
                <td>{e.type}</td>
                <td>{formaterMontant(e.cout)}</td>
              </tr>
            ))}
            {stats.derniers_entretiens.length === 0 && (
              <tr><td colSpan="4" className="vide">Aucun entretien enregistré</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

function DashboardChauffeur({ user, allerA }) {
  const [stats, setStats] = useState(null);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    const charger = () => api("/api/stats-chauffeur/").then(setStats).catch((e) => setErreur(e.message));
    charger();
    const t = setInterval(charger, 10000);
    return () => clearInterval(t);
  }, []);

  if (erreur) return <Message type="erreur" texte={erreur} />;
  if (!stats) return <p>Chargement…</p>;

  const cartes = [
    { libelle: "Mes véhicules", valeur: stats.nb_vehicules },
    { libelle: "Pannes signalées", valeur: stats.nb_pannes },
    { libelle: "Réparations demandées", valeur: stats.nb_reparations },
    { libelle: "En attente", valeur: stats.par_statut.en_attente },
    { libelle: "En cours", valeur: stats.par_statut.en_cours },
    { libelle: "Traitées", valeur: stats.par_statut.traitee },
  ];

  return (
    <>
      <div className="carte">
        <h2>Bonjour {user.username}</h2>
        {stats.nb_vehicules === 0 ? (
          <p>Aucun véhicule ne vous est attribué pour le moment. L'administrateur doit vous en affecter un.</p>
        ) : (
          <p>
            Véhicule(s) attribué(s) :{" "}
            <strong>{stats.vehicules.map((v) => v.marque + " " + v.modele + " (" + v.immatriculation + ")").join(", ")}</strong>
          </p>
        )}
        <div className="actions">
          <button className="btn" onClick={() => allerA("mes_vehicules")}>Mes véhicules</button>
          <button className="btn sec" onClick={() => allerA("mes_signalements")}>Mes signalements</button>
        </div>
      </div>

      <div className="grille">
        {cartes.map((c) => (
          <div className="stat" key={c.libelle}>
            <div className="valeur">{c.valeur}</div>
            <div className="libelle">{c.libelle}</div>
          </div>
        ))}
      </div>

      <div className="carte">
        <h2>Mes derniers signalements</h2>
        <table>
          <thead>
            <tr><th>Date</th><th>Véhicule</th><th>Type</th><th>Statut</th></tr>
          </thead>
          <tbody>
            {stats.derniers_signalements.map((x) => (
              <tr key={x.id}>
                <td>{formaterDate(x.date)}</td>
                <td>{x.vehicule_libelle} ({x.vehicule})</td>
                <td>{x.type_libelle}</td>
                <td><Badge statut={x.statut} libelle={x.statut_libelle} /></td>
              </tr>
            ))}
            {stats.derniers_signalements.length === 0 && (
              <tr><td colSpan="4" className="vide">Aucun signalement pour le moment</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

const VEHICULE_VIDE = { immatriculation: "", marque: "", modele: "", annee: 2022, kilometrage: 0, statut: "disponible" };

function Vehicules() {
  const [recherche, setRecherche] = useState("");
  const [filtreStatut, setFiltreStatut] = useState("");
  const url = "/api/vehicules/?search=" + encodeURIComponent(recherche) + "&statut=" + filtreStatut;
  const [vehicules, recharger, erreurListe] = useListe(url);
  const p = usePagination(vehicules, recherche + "|" + filtreStatut);

  const [form, setForm] = useState(VEHICULE_VIDE);
  const [enEdition, setEnEdition] = useState(null);
  const [message, setMessage] = useState({ type: "", texte: "" });

  const changer = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  function annuler() {
    setEnEdition(null);
    setForm(VEHICULE_VIDE);
  }

  async function soumettre(e) {
    e.preventDefault();
    try {
      if (enEdition) {
        await api("/api/vehicules/" + enEdition + "/", "PUT", form);
        setMessage({ type: "ok", texte: "Véhicule modifié" });
      } else {
        await api("/api/vehicules/", "POST", form);
        setMessage({ type: "ok", texte: "Véhicule ajouté" });
      }
      annuler();
      recharger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  function modifier(v) {
    setEnEdition(v.immatriculation);
    setForm({ ...v });
    setMessage({ type: "", texte: "" });
  }

  async function supprimer(v) {
    if (!window.confirm("Supprimer " + v.immatriculation + " ?")) return;
    try {
      await api("/api/vehicules/" + encodeURIComponent(v.immatriculation) + "/", "DELETE");
      recharger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  return (
    <>
      <div className="carte">
        <h2>{enEdition ? "Modifier le véhicule " + enEdition : "Ajouter un véhicule"}</h2>
        <Message type={message.type} texte={message.texte} />
        <form className="formulaire" onSubmit={soumettre}>
          <Champ label="Immatriculation">
            <input name="immatriculation" value={form.immatriculation} onChange={changer}
                   readOnly={enEdition !== null} maxLength={15} required />
          </Champ>
          <Champ label="Marque">
            <input name="marque" value={form.marque} onChange={changer} required />
          </Champ>
          <Champ label="Modèle">
            <input name="modele" value={form.modele} onChange={changer} required />
          </Champ>
          <Champ label="Année">
            <input name="annee" type="number" value={form.annee} onChange={changer} />
          </Champ>
          <Champ label="Kilométrage">
            <input name="kilometrage" type="number" min="0" value={form.kilometrage} onChange={changer} />
          </Champ>
          <Champ label="Statut">
            <select name="statut" value={form.statut} onChange={changer}>
              {Object.keys(LIBELLES_STATUT).map((code) => (
                <option key={code} value={code}>{LIBELLES_STATUT[code]}</option>
              ))}
            </select>
          </Champ>
          <div className="actions">
            <button className="btn" type="submit">{enEdition ? "Enregistrer" : "Ajouter"}</button>
            {enEdition && <button className="btn sec" type="button" onClick={annuler}>Annuler</button>}
          </div>
        </form>
      </div>

      <div className="carte">
        <h2>Liste des véhicules</h2>
        <div className="barre">
          <input type="search" placeholder="Rechercher (immat., marque, modèle)…"
                 value={recherche} onChange={(e) => setRecherche(e.target.value)} />
          <select value={filtreStatut} onChange={(e) => setFiltreStatut(e.target.value)}>
            <option value="">Tous les statuts</option>
            {Object.keys(LIBELLES_STATUT).map((code) => (
              <option key={code} value={code}>{LIBELLES_STATUT[code]}</option>
            ))}
          </select>
        </div>
        <Message type="erreur" texte={erreurListe} />
        <table>
          <thead>
            <tr><th>Immat.</th><th>Marque</th><th>Modèle</th><th>Année</th><th>Km</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            {p.visibles.map((v) => (
              <tr key={v.immatriculation}>
                <td>{v.immatriculation}</td>
                <td>{v.marque}</td>
                <td>{v.modele}</td>
                <td>{v.annee}</td>
                <td>{Number(v.kilometrage).toLocaleString("fr-FR")}</td>
                <td><Badge statut={v.statut} /></td>
                <td className="actions">
                  <button className="btn sec petit" onClick={() => modifier(v)}>Modifier</button>
                  <button className="btn danger petit" onClick={() => supprimer(v)}>Supprimer</button>
                </td>
              </tr>
            ))}
            {vehicules.length === 0 && <tr><td colSpan="7" className="vide">Aucun résultat !</td></tr>}
          </tbody>
        </table>
        <Pagination p={p} />
      </div>
    </>
  );
}

const CHAUFFEUR_VIDE = { username: "", prenom: "", nom: "", telephone: "", permis: "", password: "", confirmation: "" };

function Chauffeurs() {
  const [recherche, setRecherche] = useState("");
  const [chauffeurs, recharger, erreurListe] = useListe("/api/chauffeurs/?search=" + encodeURIComponent(recherche));
  const p = usePagination(chauffeurs, recherche);

  useEffect(() => {
    const t = setInterval(recharger, 10000);
    return () => clearInterval(t);
  }, [recherche]);

  const [form, setForm] = useState(CHAUFFEUR_VIDE);
  const [enEdition, setEnEdition] = useState(null);
  const [message, setMessage] = useState({ type: "", texte: "" });

  const changer = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  function annuler() {
    setEnEdition(null);
    setForm(CHAUFFEUR_VIDE);
  }

  async function soumettre(e) {
    e.preventDefault();
    if (form.password !== form.confirmation) {
      setMessage({ type: "erreur", texte: "Les deux mots de passe ne sont pas identiques" });
      return;
    }
    try {
      if (enEdition) await api("/api/chauffeurs/" + enEdition + "/", "PUT", form);
      else await api("/api/chauffeurs/", "POST", form);
      setMessage({ type: "ok", texte: enEdition ? "Chauffeur modifié" : "Chauffeur ajouté" });
      annuler();
      recharger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  async function supprimer(c) {
    if (!window.confirm("Supprimer " + c.nom_complet + " et son compte ?")) return;
    await api("/api/chauffeurs/" + c.numero + "/", "DELETE");
    recharger();
  }

  function modifier(c) {
    setEnEdition(c.numero);
    setForm({
      username: c.compte, prenom: c.prenom, nom: c.nom, telephone: c.telephone, permis: c.permis,
      password: "", confirmation: "",
    });
    setMessage({ type: "", texte: "" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <>
      <div className="carte">
        <h2>{enEdition ? "Modifier le chauffeur" : "Ajouter un chauffeur"}</h2>
        <Message type={message.type} texte={message.texte} />
        <form className="formulaire" onSubmit={soumettre}>
          <Champ label="Identifiant">
            <input name="username" value={form.username} onChange={changer} maxLength={30}
                   required={!enEdition || form.username !== ""} />
          </Champ>
          <Champ label="Prénom">
            <input name="prenom" value={form.prenom} onChange={changer} maxLength={30} />
          </Champ>
          <Champ label="Nom">
            <input name="nom" value={form.nom} onChange={changer} maxLength={30} />
          </Champ>
          <Champ label="Téléphone">
            <input name="telephone" value={form.telephone} onChange={changer} {...PROPS_TEL} />
          </Champ>
          <Champ label="N° de permis">
            <input name="permis" value={form.permis} onChange={changer} maxLength={30} />
          </Champ>
          <Champ label={enEdition ? "Nouveau mot de passe" : "Mot de passe"}>
            <input name="password" type="password" value={form.password} onChange={changer}
                   placeholder={enEdition ? "Laisser vide pour ne pas changer" : ""}
                   autoComplete="new-password" required={!enEdition} />
          </Champ>
          <Champ label="Confirmer le mot de passe">
            <input name="confirmation" type="password" value={form.confirmation} onChange={changer}
                   autoComplete="new-password" required={!enEdition || form.password !== ""} />
          </Champ>
          <div className="actions">
            <button className="btn" type="submit">{enEdition ? "Enregistrer" : "Ajouter"}</button>
            {enEdition && <button className="btn sec" type="button" onClick={annuler}>Annuler</button>}
          </div>
        </form>
      </div>

      <div className="carte">
        <h2>Liste des chauffeurs ({chauffeurs.length})</h2>
        <div className="barre">
          <input type="search" placeholder="Rechercher (nom, permis, identifiant)…" value={recherche}
                 onChange={(e) => setRecherche(e.target.value)} />
          <button className="btn sec" onClick={recharger}>Actualiser</button>
        </div>
        <Message type="erreur" texte={erreurListe} />
        <table>
          <thead><tr><th>N°</th><th>Nom</th><th>Téléphone</th><th>Permis</th><th>Compte</th><th>Inscrit le</th><th></th></tr></thead>
          <tbody>
            {p.visibles.map((c) => (
              <tr key={c.numero}>
                <td>{c.numero}</td><td>{c.nom_complet}</td><td>{c.telephone}</td><td>{c.permis}</td>
                <td>{c.compte || "—"}</td><td>{formaterDate(c.date_inscription)}</td>
                <td className="actions">
                  <button className="btn sec petit" onClick={() => modifier(c)}>Modifier</button>
                  <button className="btn danger petit" onClick={() => supprimer(c)}>Supprimer</button>
                </td>
              </tr>
            ))}
            {chauffeurs.length === 0 && <tr><td colSpan="7" className="vide">Aucun résultat !</td></tr>}
          </tbody>
        </table>
        <Pagination p={p} />
      </div>
    </>
  );
}

const estTerminee = (a) => Boolean(a.date_fin) && a.date_fin <= aujourdhui();

function Affectations() {
  const [affectations, recharger, erreurListe] = useListe("/api/affectations/");
  const [vehicules, rechargerVehicules] = useListe("/api/vehicules/");
  const [chauffeurs] = useListe("/api/chauffeurs/");
  const p = usePagination(affectations);
  const [form, setForm] = useState({ vehicule: "", chauffeur: "", date_debut: "" });
  const [message, setMessage] = useState({ type: "", texte: "" });

  const disponibles = vehicules.filter((v) => v.statut === "disponible");

  const changer = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  function toutRecharger() {
    recharger();
    rechargerVehicules();
  }

  async function soumettre(e) {
    e.preventDefault();
    try {
      await api("/api/affectations/", "POST", form);
      setMessage({ type: "ok", texte: "Affectation enregistrée" });
      setForm({ vehicule: "", chauffeur: "", date_debut: "" });
      toutRecharger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  async function cloturer(a) {
    try {
      await api("/api/affectations/" + a.id + "/", "PUT", {});
      setMessage({ type: "ok", texte: "Affectation terminée : le véhicule n'apparaît plus chez le chauffeur" });
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
    toutRecharger();
  }

  async function supprimer(a) {
    if (!window.confirm("Supprimer cette affectation ?")) return;
    await api("/api/affectations/" + a.id + "/", "DELETE");
    toutRecharger();
  }

  return (
    <>
      <div className="carte">
        <h2>Nouvelle affectation</h2>
        <Message type={message.type} texte={message.texte} />
        <form className="formulaire" onSubmit={soumettre}>
          <Champ label="Véhicule disponible">
            <select name="vehicule" value={form.vehicule} onChange={changer} required>
              <option value="">— choisir —</option>
              {disponibles.map((v) => (
                <option key={v.immatriculation} value={v.immatriculation}>
                  {v.immatriculation} — {v.marque} {v.modele}
                </option>
              ))}
            </select>
          </Champ>
          <Champ label="Chauffeur">
            <select name="chauffeur" value={form.chauffeur} onChange={changer} required>
              <option value="">— choisir —</option>
              {chauffeurs.map((c) => <option key={c.numero} value={c.numero}>{c.nom_complet}</option>)}
            </select>
          </Champ>
          <Champ label="Date de début">
            <input type="date" name="date_debut" min={aujourdhui()} value={form.date_debut} onChange={changer} required />
          </Champ>
          <div className="actions"><button className="btn" type="submit">Affecter</button></div>
        </form>
      </div>

      <div className="carte">
        <h2>Historique des affectations</h2>
        <Message type="erreur" texte={erreurListe} />
        <table>
          <thead>
            <tr><th>Véhicule</th><th>Chauffeur</th><th>Début</th><th>Fin</th><th>Statut</th><th></th></tr>
          </thead>
          <tbody>
            {p.visibles.map((a) => (
              <tr key={a.id}>
                <td>{a.vehicule} — {a.vehicule_libelle}</td>
                <td>{a.chauffeur_nom}</td>
                <td>{formaterDate(a.date_debut)}</td>
                <td>{formaterDate(a.date_fin)}</td>
                <td>
                  {estTerminee(a) ? <Badge statut="hors_service" libelle="Terminée" /> : <Badge statut="affecte" libelle="En cours" />}
                </td>
                <td className="actions">
                  {!estTerminee(a) && (
                    <button className="btn sec petit" onClick={() => cloturer(a)}>Retour du véhicule</button>
                  )}
                  <button className="btn danger petit" onClick={() => supprimer(a)}>Supprimer</button>
                </td>
              </tr>
            ))}
            {affectations.length === 0 && <tr><td colSpan="6" className="vide">Aucune affectation</td></tr>}
          </tbody>
        </table>
        <Pagination p={p} />
      </div>
    </>
  );
}

const ENTRETIEN_VIDE = { vehicule: "", type: "Vidange", date: "", cout: "", description: "" };
const TYPES_ENTRETIEN = ["Vidange", "Révision", "Pneus", "Freins", "Réparation", "Contrôle technique"];

function Entretiens() {
  const [entretiens, recharger, erreurListe] = useListe("/api/entretiens/");
  const [vehicules] = useListe("/api/vehicules/");
  const p = usePagination(entretiens);
  const [form, setForm] = useState(ENTRETIEN_VIDE);
  const [message, setMessage] = useState({ type: "", texte: "" });

  const total = entretiens.reduce((acc, e) => acc + e.cout, 0);
  const changer = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function soumettre(e) {
    e.preventDefault();
    try {
      await api("/api/entretiens/", "POST", form);
      setMessage({ type: "ok", texte: "Entretien enregistré" });
      setForm(ENTRETIEN_VIDE);
      recharger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  async function supprimer(e) {
    if (!window.confirm("Supprimer cet entretien ?")) return;
    await api("/api/entretiens/" + e.id + "/", "DELETE");
    recharger();
  }

  return (
    <>
      <div className="carte">
        <h2>Nouvel entretien</h2>
        <Message type={message.type} texte={message.texte} />
        <form className="formulaire" onSubmit={soumettre}>
          <Champ label="Véhicule">
            <select name="vehicule" value={form.vehicule} onChange={changer} required>
              <option value="">— choisir —</option>
              {vehicules.map((v) => (
                <option key={v.immatriculation} value={v.immatriculation}>
                  {v.immatriculation} — {v.marque} {v.modele}
                </option>
              ))}
            </select>
          </Champ>
          <Champ label="Type">
            <select name="type" value={form.type} onChange={changer}>
              {TYPES_ENTRETIEN.map((t) => <option key={t}>{t}</option>)}
            </select>
          </Champ>
          <Champ label="Date">
            <input type="date" name="date" min={aujourdhui()} value={form.date} onChange={changer} required />
          </Champ>
          <Champ label="Coût (Ar)">
            <input type="number" min="1" step="1" name="cout" value={form.cout} onChange={changer} required />
          </Champ>
          <Champ label="Description">
            <input name="description" value={form.description} onChange={changer} />
          </Champ>
          <div className="actions"><button className="btn" type="submit">Enregistrer</button></div>
        </form>
      </div>

      <div className="carte">
        <h2>Historique des entretiens — total : {formaterMontant(total)}</h2>
        <Message type="erreur" texte={erreurListe} />
        <table>
          <thead>
            <tr><th>Date</th><th>Véhicule</th><th>Type</th><th>Description</th><th>Coût</th><th></th></tr>
          </thead>
          <tbody>
            {p.visibles.map((e) => (
              <tr key={e.id}>
                <td>{formaterDate(e.date)}</td>
                <td>{e.vehicule} — {e.vehicule_libelle}</td>
                <td>{e.type}</td>
                <td>{e.description}</td>
                <td>{formaterMontant(e.cout)}</td>
                <td><button className="btn danger petit" onClick={() => supprimer(e)}>Supprimer</button></td>
              </tr>
            ))}
            {entretiens.length === 0 && <tr><td colSpan="6" className="vide">Aucun entretien</td></tr>}
          </tbody>
        </table>
        <Pagination p={p} />
      </div>
    </>
  );
}

function MesVehicules() {
  const [vehicules, recharger, erreurListe] = useListe("/api/mes-vehicules/");
  const p = usePagination(vehicules);
  const [choisi, setChoisi] = useState(null);

  useEffect(() => {
    const t = setInterval(recharger, 10000);
    return () => clearInterval(t);
  }, []);

  if (choisi) return <DetailVehicule immat={choisi} retour={() => setChoisi(null)} />;

  return (
    <div className="carte">
      <h2>Mes véhicules</h2>
      <Message type="erreur" texte={erreurListe} />
      <table>
        <thead>
          <tr><th>Immat.</th><th>Marque</th><th>Modèle</th><th>Statut</th><th>Attribué depuis</th><th></th></tr>
        </thead>
        <tbody>
          {p.visibles.map((v) => (
            <tr key={v.immatriculation}>
              <td>{v.immatriculation}</td>
              <td>{v.marque}</td>
              <td>{v.modele}</td>
              <td><Badge statut={v.statut} /></td>
              <td>{formaterDate(v.depuis)}</td>
              <td className="actions">
                <button className="btn petit" onClick={() => setChoisi(v.immatriculation)}>Détails</button>
              </td>
            </tr>
          ))}
          {vehicules.length === 0 && (
            <tr><td colSpan="6" className="vide">Aucun véhicule ne vous est attribué pour le moment</td></tr>
          )}
        </tbody>
      </table>
      <Pagination p={p} />
    </div>
  );
}

const SIGNALEMENT_VIDE = { type: "panne", description: "" };
const TYPES_SIGNALEMENT = { panne: "Signaler une panne", reparation: "Demander une réparation" };

function DetailVehicule({ immat, retour }) {
  const [v, setV] = useState(null);
  const [erreur, setErreur] = useState("");
  const [form, setForm] = useState(SIGNALEMENT_VIDE);
  const [message, setMessage] = useState({ type: "", texte: "" });
  const pe = usePagination(v ? v.entretiens : []);
  const ps = usePagination(v ? v.signalements : []);

  function charger() {
    api("/api/mes-vehicules/" + encodeURIComponent(immat) + "/").then(setV).catch((e) => setErreur(e.message));
  }
  useEffect(() => {
    charger();
    const t = setInterval(charger, 10000);
    return () => clearInterval(t);
  }, [immat]);

  const changer = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  async function soumettre(e) {
    e.preventDefault();
    try {
      await api("/api/signalements/", "POST", { ...form, vehicule: immat });
      setMessage({
        type: "ok",
        texte: form.type === "panne" ? "Panne signalée à l'administrateur" : "Demande de réparation envoyée",
      });
      setForm(SIGNALEMENT_VIDE);
      charger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  if (erreur) return <><Message type="erreur" texte={erreur} /><button className="btn sec" onClick={retour}>← Retour</button></>;
  if (!v) return <p>Chargement…</p>;

  return (
    <>
      <button className="btn sec" style={{ marginBottom: 16 }} onClick={retour}>← Mes véhicules</button>

      <div className="carte">
        <h2>{v.marque} {v.modele} — {v.immatriculation}</h2>
        <div className="grille">
          <div className="stat"><div className="valeur">{v.annee}</div><div className="libelle">Année</div></div>
          <div className="stat">
            <div className="valeur">{Number(v.kilometrage).toLocaleString("fr-FR")}</div>
            <div className="libelle">Kilométrage (km)</div>
          </div>
          <div className="stat"><div className="valeur"><Badge statut={v.statut} /></div><div className="libelle">Statut</div></div>
          <div className="stat">
            <div className="valeur">{formaterDate(v.depuis)}</div>
            <div className="libelle">Attribué depuis{v.jusqu_au ? " (jusqu'au " + formaterDate(v.jusqu_au) + ")" : ""}</div>
          </div>
        </div>
      </div>

      <div className="carte">
        <h2>Signaler une panne ou demander une réparation</h2>
        <Message type={message.type} texte={message.texte} />
        <form className="formulaire" onSubmit={soumettre}>
          <Champ label="Je souhaite">
            <select name="type" value={form.type} onChange={changer}>
              {Object.keys(TYPES_SIGNALEMENT).map((code) => (
                <option key={code} value={code}>{TYPES_SIGNALEMENT[code]}</option>
              ))}
            </select>
          </Champ>
          <Champ label="Description du problème">
            <textarea name="description" rows={3} maxLength={500} value={form.description} onChange={changer}
                      placeholder="Que se passe-t-il ? Depuis quand ? Où êtes-vous ?" required />
          </Champ>
          <div className="actions"><button className="btn" type="submit">Envoyer</button></div>
        </form>
      </div>

      <div className="carte">
        <h2>Historique d'entretien</h2>
        <table>
          <thead><tr><th>Date</th><th>Type</th><th>Description</th></tr></thead>
          <tbody>
            {pe.visibles.map((e) => (
              <tr key={e.id}><td>{formaterDate(e.date)}</td><td>{e.type}</td><td>{e.description}</td></tr>
            ))}
            {v.entretiens.length === 0 && <tr><td colSpan="3" className="vide">Aucun entretien enregistré</td></tr>}
          </tbody>
        </table>
        <Pagination p={pe} />
      </div>

      <div className="carte">
        <h2>Mes signalements pour ce véhicule</h2>
        <table>
          <thead><tr><th>Date</th><th>Type</th><th>Description</th><th>Statut</th></tr></thead>
          <tbody>
            {ps.visibles.map((x) => (
              <tr key={x.id}>
                <td>{formaterDate(x.date)}</td>
                <td>{x.type_libelle}</td>
                <td>{x.description}</td>
                <td><Badge statut={x.statut} libelle={x.statut_libelle} /></td>
              </tr>
            ))}
            {v.signalements.length === 0 && <tr><td colSpan="4" className="vide">Aucun signalement</td></tr>}
          </tbody>
        </table>
        <Pagination p={ps} />
      </div>
    </>
  );
}

const STATUTS_SIGNALEMENT = {
  en_attente: "En attente", en_cours: "En cours de traitement", traitee: "Traitée", refusee: "Refusée",
};
const FILTRES_TYPE = { panne: "Pannes", reparation: "Demandes de réparation" };

function Signalements({ admin }) {
  const [filtreStatut, setFiltreStatut] = useState("");
  const [filtreType, setFiltreType] = useState("");
  const [signalements, recharger, erreurListe] = useListe(
    "/api/signalements/?statut=" + filtreStatut + "&type=" + filtreType
  );
  const p = usePagination(signalements, filtreStatut + "|" + filtreType);
  const [message, setMessage] = useState({ type: "", texte: "" });

  useEffect(() => {
    if (!admin) return;
    const t = setInterval(recharger, 10000);
    return () => clearInterval(t);
  }, [admin, filtreStatut, filtreType]);

  async function changerStatut(s, statut) {
    try {
      await api("/api/signalements/" + s.id + "/", "PUT", { statut });
      setMessage({ type: "", texte: "" });
      recharger();
    } catch (err) {
      setMessage({ type: "erreur", texte: err.message });
    }
  }

  return (
    <div className="carte">
      <h2>{admin ? "Pannes et demandes de réparation" : "Mes signalements"} ({signalements.length})</h2>
      <Message type={message.type} texte={message.texte} />
      <div className="barre">
        <select value={filtreType} onChange={(e) => setFiltreType(e.target.value)}>
          <option value="">Tous les types</option>
          {Object.keys(FILTRES_TYPE).map((code) => <option key={code} value={code}>{FILTRES_TYPE[code]}</option>)}
        </select>
        <select value={filtreStatut} onChange={(e) => setFiltreStatut(e.target.value)}>
          <option value="">Tous les statuts</option>
          {Object.keys(STATUTS_SIGNALEMENT).map((code) => (
            <option key={code} value={code}>{STATUTS_SIGNALEMENT[code]}</option>
          ))}
        </select>
        <button className="btn sec" onClick={recharger}>Actualiser</button>
      </div>
      <Message type="erreur" texte={erreurListe} />
      <table>
        <thead>
          <tr>
            <th>Date</th><th>Véhicule</th>
            {admin && <th>Chauffeur</th>}
            <th>Type</th><th>Description</th><th>Statut</th>
            {admin && <th></th>}
          </tr>
        </thead>
        <tbody>
          {p.visibles.map((s) => (
            <tr key={s.id}>
              <td>{formaterDate(s.date)}</td>
              <td>{s.vehicule_libelle} ({s.vehicule})</td>
              {admin && <td>{s.chauffeur_nom}</td>}
              <td>{s.type_libelle}</td>
              <td>{s.description}</td>
              <td><Badge statut={s.statut} libelle={s.statut_libelle} /></td>
              {admin && (
                <td className="actions">
                  {s.statut === "en_attente" && (
                    <>
                      <button className="btn petit" onClick={() => changerStatut(s, "en_cours")}>Prendre en charge</button>
                      <button className="btn danger petit" onClick={() => changerStatut(s, "refusee")}>Refuser</button>
                    </>
                  )}
                  {s.statut === "en_cours" && (
                    <button className="btn petit" onClick={() => changerStatut(s, "traitee")}>Marquer comme traité</button>
                  )}
                </td>
              )}
            </tr>
          ))}
          {signalements.length === 0 && (
            <tr><td colSpan={admin ? 7 : 5} className="vide">Aucun signalement</td></tr>
          )}
        </tbody>
      </table>
      <Pagination p={p} />
    </div>
  );
}

const PAGES = [
  { cle: "dashboard", titre: "Tableau de bord", roles: ["admin"] },
  { cle: "dashboard_chauffeur", titre: "Tableau de bord", roles: ["chauffeur"] },
  { cle: "vehicules", titre: "Véhicules", roles: ["admin"] },
  { cle: "chauffeurs", titre: "Chauffeurs", roles: ["admin"] },
  { cle: "affectations", titre: "Affectations", roles: ["admin"] },
  { cle: "entretiens", titre: "Entretiens", roles: ["admin"] },
  { cle: "signalements", titre: "Pannes et réparations", roles: ["admin"] },
  { cle: "mes_vehicules", titre: "Mes véhicules", roles: ["chauffeur"] },
  { cle: "mes_signalements", titre: "Mes signalements", roles: ["chauffeur"] },
];

const LIBELLES_ROLE = { admin: "Administrateur", chauffeur: "Chauffeur" };

const FORM_VIDE = { username: "", prenom: "", nom: "", telephone: "", permis: "", password: "", confirmation: "" };

function Login({ onConnecte, erreurInitiale }) {
  const [inscription, setInscription] = useState(false);
  const [form, setForm] = useState(FORM_VIDE);
  const [erreur, setErreur] = useState(erreurInitiale);

  const changer = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  function basculer() {
    setInscription(!inscription);
    setForm(FORM_VIDE);
    setErreur("");
  }

  async function soumettre(e) {
    e.preventDefault();
    try {
      let utilisateur;
      if (inscription) {
        if (form.password !== form.confirmation) {
          setErreur("Les deux mots de passe ne sont pas identiques");
          return;
        }
        utilisateur = await api("/api/inscription/", "POST", form);
      } else {
        utilisateur = await api("/api/connexion/", "POST", form);
      }
      onConnecte(utilisateur);
    } catch (err) {
      setErreur(err.message);
    }
  }

  return (
    <div className="connexion">
      <form className="carte" onSubmit={soumettre}>
        <h2>{inscription ? "Créer un compte chauffeur" : "Gestion de parc automobile"}</h2>
        <Message type="erreur" texte={erreur} />

        <Champ label="Identifiant">
          <input name="username" value={form.username} onChange={changer} required autoFocus />
        </Champ>

        {inscription && (
          <>
            <Champ label="Prénom">
              <input name="prenom" value={form.prenom} onChange={changer} />
            </Champ>
            <Champ label="Nom">
              <input name="nom" value={form.nom} onChange={changer} />
            </Champ>
            <Champ label="Téléphone">
              <input name="telephone" value={form.telephone} onChange={changer} {...PROPS_TEL} />
            </Champ>
            <Champ label="N° de permis">
              <input name="permis" value={form.permis} onChange={changer} maxLength={30} />
            </Champ>
          </>
        )}

        <Champ label="Mot de passe">
          <input name="password" type="password" value={form.password} onChange={changer} required />
        </Champ>

        {inscription && (
          <Champ label="Confirmer le mot de passe">
            <input name="confirmation" type="password" value={form.confirmation} onChange={changer} required />
          </Champ>
        )}

        <button className="btn" type="submit">{inscription ? "Créer mon compte" : "Se connecter"}</button>
        <button className="lien" type="button" onClick={basculer}>
          {inscription ? "J'ai déjà un compte : me connecter" : "Pas de compte ? Créer un compte"}
        </button>
      </form>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [pret, setPret] = useState(false);
  const [erreurInit, setErreurInit] = useState("");

  function demarrer(utilisateur) {
    setUser(utilisateur);
    setPage(utilisateur.role === "admin" ? "dashboard" : "dashboard_chauffeur");
  }

  useEffect(() => {
    api("/api/csrf/")
      .then(() => api("/api/moi/"))
      .then((d) => { if (d.connecte) demarrer(d); })
      .catch((e) => setErreurInit(e.message))
      .finally(() => setPret(true));
  }, []);

  async function deconnecter() {
    await api("/api/deconnexion/", "POST");
    setUser(null);
  }

  if (!pret) return <p style={{ padding: 24 }}>Chargement…</p>;
  if (!user) return <Login onConnecte={demarrer} erreurInitiale={erreurInit} />;

  const pagesVisibles = PAGES.filter((p) => p.roles.includes(user.role));

  let contenu;
  if (page === "dashboard") contenu = <Dashboard />;
  else if (page === "dashboard_chauffeur") contenu = <DashboardChauffeur user={user} allerA={setPage} />;
  else if (page === "vehicules") contenu = <Vehicules />;
  else if (page === "mes_vehicules") contenu = <MesVehicules />;
  else if (page === "chauffeurs") contenu = <Chauffeurs />;
  else if (page === "affectations") contenu = <Affectations />;
  else if (page === "signalements" || page === "mes_signalements") contenu = <Signalements admin={user.role === "admin"} />;
  else contenu = <Entretiens />;

  return (
    <div className="app">

      <nav className="menu">
        <h1>Parc automobile</h1>
        {pagesVisibles.map((p) => (
          <button key={p.cle} className={page === p.cle ? "actif" : ""} onClick={() => setPage(p.cle)}>
            {p.titre}
          </button>
        ))}

        <div className="utilisateur">
          <div><strong>{user.username}</strong></div>
          <div>{LIBELLES_ROLE[user.role]}</div>
          <button onClick={deconnecter}>Se déconnecter</button>
        </div>
      </nav>

      <main className="contenu">{contenu}</main>
    </div>
  );
}
