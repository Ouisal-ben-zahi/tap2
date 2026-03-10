
import React, { useState } from "react";
import "../css/Dashboard.css";
import {
  LayoutDashboard,
  BriefcaseBusiness,
  Users,
  BarChart2,
  Bell,
  Search,
  LogOut,
} from "lucide-react";
import logo from "../assets/logo-white.svg";

const MENU = [
  { id: "overview", label: "Vue d’ensemble", icon: LayoutDashboard },
  { id: "jobs", label: "Mes offres", icon: BriefcaseBusiness },
  { id: "applications", label: "Candidatures", icon: BarChart2 },
  { id: "candidates", label: "Base candidats", icon: Users },
  { id: "activity", label: "Activité récente", icon: Bell },
];

export default function DashboardRecruteur() {
  const [active, setActive] = useState("overview");
  const [showJobForm, setShowJobForm] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [jobForm, setJobForm] = useState({
    title: "",
    categorie_profil: "",
    niveau_attendu: "",
    experience_min: "",
    presence_sur_site: "",
    reason: "",
    main_mission: "",
    tasks_other: "",
    disponibilite: "",
    salary_min: "",
    salary_max: "",
    urgent: false,
    contrat: "stage",
    niveau_seniorite: "",
    entreprise: "",
  });

  const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

  React.useEffect(() => {
    if (active !== "jobs") return;
    const userId = sessionStorage.getItem("userId");
    if (!userId) return;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/recruteur/${userId}/jobs`);
        const data = await res.json().catch(() => null);
        if (res.ok && data && Array.isArray(data.jobs)) {
          setJobs(data.jobs);
        }
      } catch {
        // ignore pour l’instant
      }
    })();
  }, [active]);

  const fakeStats = {
    totalJobs: 3,
    totalCandidates: 25,
    totalApplications: 42,
    validatedApplications: 10,
    pendingApplications: 32,
  };

  const logout = () => {
    ["authToken","profileType","userEmail","userId","userName"].forEach(k => sessionStorage.removeItem(k));
    window.location.href = "/connexion";
  };

  return (
    <section className="dash-section">
      <div className="dash-layout">
        {/* SIDEBAR recruteur, même style que candidat */}
        <aside className="dash-sidebar">
          <div className="dash-logo-zone">
            <img src={logo} alt="Logo TAP" className="dash-logo-img" />
          </div>

          <nav className="dash-nav">
            <div className="dash-nav-section-label">Recruteur</div>
            {MENU.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                data-label={label}
                className={`dash-menu-item${
                  active === id ? " dash-menu-item--active" : ""
                }`}
                onClick={() => setActive(id)}
              >
                <span className="dash-menu-icon">
                  <Icon size={18} strokeWidth={active === id ? 2 : 1.6} />
                </span>
                <span className="dash-menu-label">{label}</span>
              </button>
            ))}
          </nav>

          <div className="dash-sidebar-footer">
            <button type="button" className="dash-logout" onClick={logout}>
              <LogOut size={17} strokeWidth={1.6} />
              <span className="dash-logout-label">Se déconnecter</span>
            </button>
          </div>
        </aside>

        {/* MAIN */}
        <main className="dash-main">
          {/* TOPBAR */}
          <div className="dash-topbar">
            <div className="dash-topbar-left">
              <div className="dash-breadcrumb">
                <span>Espace</span>
                <span className="dash-breadcrumb-sep">›</span>
                <span className="dash-breadcrumb-current">Dashboard recruteur</span>
              </div>
            </div>
            <div className="dash-topbar-right">
              <div className="dash-search-wrap">
                <Search size={14} color="var(--t3)" />
                <input
                  type="search"
                  className="dash-search"
                  placeholder="Rechercher un candidat…"
                />
              </div>
              <div className="dash-notif-wrap">
                <Bell size={18} strokeWidth={1.6} />
              </div>
            </div>
          </div>

          {/* CONTENU selon l’onglet actif */}
          {/* Overview */}
          {active === "overview" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Vue d’ensemble recruteur</h1>
                <p className="dash-page-sub">
                  Suivez vos offres et candidatures en temps réel.
                </p>
              </div>

              <div className="dash-cards-row">
                <div className="dash-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Jobs postés</span>
                    <div className="dash-card-icon-wrap">
                      <BriefcaseBusiness size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {fakeStats.totalJobs ?? "—"}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Candidats</span>
                    <div className="dash-card-icon-wrap">
                      <Users size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {fakeStats.totalCandidates ?? "—"}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Candidatures</span>
                    <div className="dash-card-icon-wrap">
                      <LayoutDashboard size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {fakeStats.totalApplications ?? "—"}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Validées</span>
                    <div className="dash-card-icon-wrap">
                      <BarChart2 size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {fakeStats.validatedApplications ?? "—"}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">En attente</span>
                    <div className="dash-card-icon-wrap">
                      <BarChart2 size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {fakeStats.pendingApplications ?? "—"}
                  </div>
                </div>
              </div>

              <div className="dash-section-page">
                <div className="dash-section-card">
                  <p>
                    Ici viendront les graphiques et tableaux (jobs, candidatures)
                    pour le dashboard recruteur, avec le même design que le dashboard candidat.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Placeholder pour les autres onglets, à compléter plus tard */}
          {active === "jobs" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Mes offres</h1>
                <p className="dash-page-sub">
                  Créez et gérez vos offres d’emploi.
                </p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  <div className="jobs-header-actions">
                    <button
                      type="button"
                      className="jobs-add-offer-btn"
                      onClick={() => setShowJobForm((v) => !v)}
                    >
                      {showJobForm ? "Masquer le formulaire" : "Ajouter une offre"}
                    </button>
                  </div>

                  {showJobForm && (
                    <form
                      style={{ marginTop: 16 }}
                      onSubmit={async (e) => {
                        e.preventDefault();
                        const userId = sessionStorage.getItem("userId");
                        if (!userId) {
                          window.location.href = "/connexion";
                          return;
                        }

                        const body = {
                          title: jobForm.title,
                          categorie_profil: jobForm.categorie_profil || null,
                          niveau_attendu: jobForm.niveau_attendu || null,
                          experience_min: jobForm.experience_min || null,
                          presence_sur_site: jobForm.presence_sur_site || null,
                          reason: jobForm.reason || null,
                          main_mission: jobForm.main_mission || null,
                          tasks_other: jobForm.tasks_other || null,
                          disponibilite: jobForm.disponibilite || null,
                          salary_min: jobForm.salary_min ? Number(jobForm.salary_min) : null,
                          salary_max: jobForm.salary_max ? Number(jobForm.salary_max) : null,
                          urgent: jobForm.urgent,
                          contrat: jobForm.contrat || "stage",
                          niveau_seniorite: jobForm.niveau_seniorite || null,
                          entreprise: jobForm.entreprise || null,
                        };

                        const res = await fetch(`${API_BASE}/dashboard/recruteur/${userId}/jobs`, {
                          method: "POST",
                          headers: {
                            "Content-Type": "application/json",
                          },
                          body: JSON.stringify(body),
                        });
                        const data = await res.json().catch(() => null);
                        if (res.ok && data && data.job) {
                          setJobs((prev) => [data.job, ...prev]);
                          setJobForm({
                            title: "",
                            categorie_profil: "",
                            niveau_attendu: "",
                            experience_min: "",
                            presence_sur_site: "",
                            reason: "",
                            main_mission: "",
                            tasks_other: "",
                            disponibilite: "",
                            salary_min: "",
                            salary_max: "",
                            urgent: false,
                            contrat: "stage",
                            niveau_seniorite: "",
                            entreprise: "",
                          });
                          setShowJobForm(false);
                        }
                      }}
                    >
                      <div className="form-row">
                        <div className="form-field">
                          <label>Titre du poste</label>
                          <input
                            type="text"
                            value={jobForm.title}
                            onChange={(e) =>
                              setJobForm({ ...jobForm, title: e.target.value })
                            }
                            required
                          />
                        </div>
                        <div className="form-field">
                          <label>Catégorie</label>
                          <input
                            type="text"
                            value={jobForm.categorie_profil}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                categorie_profil: e.target.value,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="form-row">
                        <div className="form-field">
                          <label>Niveau attendu</label>
                          <input
                            type="text"
                            value={jobForm.niveau_attendu}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                niveau_attendu: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="form-field">
                          <label>Expérience minimum</label>
                          <input
                            type="text"
                            value={jobForm.experience_min}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                experience_min: e.target.value,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="form-row">
                        <div className="form-field">
                          <label>Présence sur site</label>
                          <input
                            type="text"
                            value={jobForm.presence_sur_site}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                presence_sur_site: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="form-field">
                          <label>Disponibilité</label>
                          <input
                            type="text"
                            value={jobForm.disponibilite}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                disponibilite: e.target.value,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="form-row">
                        <div className="form-field">
                          <label>Raison du recrutement</label>
                          <textarea
                            rows={2}
                            value={jobForm.reason}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                reason: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="form-field">
                          <label>Mission principale</label>
                          <textarea
                            rows={2}
                            value={jobForm.main_mission}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                main_mission: e.target.value,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="form-row">
                        <div className="form-field form-field-full">
                          <label>Autres tâches</label>
                          <textarea
                            rows={2}
                            value={jobForm.tasks_other}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                tasks_other: e.target.value,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="form-row">
                        <div className="form-field">
                          <label>Fourchette salaire (min / max)</label>
                          <div className="form-row">
                            <input
                              type="number"
                              placeholder="Min"
                              value={jobForm.salary_min}
                              onChange={(e) =>
                                setJobForm({
                                  ...jobForm,
                                  salary_min: e.target.value,
                                })
                              }
                            />
                            <input
                              type="number"
                              placeholder="Max"
                              value={jobForm.salary_max}
                              onChange={(e) =>
                                setJobForm({
                                  ...jobForm,
                                  salary_max: e.target.value,
                                })
                              }
                            />
                          </div>
                        </div>
                        <div className="form-field">
                          <label>Type de contrat</label>
                          <select
                            value={jobForm.contrat}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                contrat: e.target.value,
                              })
                            }
                          >
                            <option value="stage">Stage</option>
                            <option value="CDI">CDI</option>
                            <option value="CDD">CDD</option>
                            <option value="Freelance">Freelance</option>
                          </select>
                        </div>
                      </div>

                      <div className="form-row">
                        <div className="form-field">
                          <label>Niveau de séniorité</label>
                          <input
                            type="text"
                            value={jobForm.niveau_seniorite}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                niveau_seniorite: e.target.value,
                              })
                            }
                          />
                        </div>
                        <div className="form-field">
                          <label>Entreprise</label>
                          <input
                            type="text"
                            value={jobForm.entreprise}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                entreprise: e.target.value,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="form-field form-field-full" style={{ marginTop: 8 }}>
                        <label>
                          <input
                            type="checkbox"
                            checked={jobForm.urgent}
                            onChange={(e) =>
                              setJobForm({
                                ...jobForm,
                                urgent: e.target.checked,
                              })
                            }
                          />{" "}
                          Marquer comme urgent
                        </label>
                      </div>

                      <div className="contact-submit-wrapper" style={{ marginTop: 12 }}>
                        <button type="submit" className="contact-submit">
                          Enregistrer l&apos;offre
                        </button>
                      </div>
                    </form>
                  )}
                </div>

                {/* Table des offres (simple pour l'instant, basée sur l'état jobs) */}
                <div className="dash-section-card" style={{ marginTop: 16 }}>
                  <h2 className="dash-panel-title" style={{ marginBottom: 8 }}>
                    Liste des offres
                  </h2>
                  <div className="jobs-table-wrap">
                    <table className="jobs-table">
                      <thead>
                        <tr>
                          <th>Titre</th>
                          <th>Catégorie</th>
                          <th>Candidatures</th>
                          <th>Urgent</th>
                          <th>Publiée le</th>
                        </tr>
                      </thead>
                      <tbody>
                        {jobs.map((job) => {
                          const date =
                            job.created_at
                              ? new Date(job.created_at).toLocaleDateString("fr-FR")
                              : "-";
                          return (
                            <tr key={job.id}>
                              <td className="jobs-col-title">{job.title}</td>
                              <td>{job.categorie_profil || "-"}</td>
                              <td>
                                {typeof job.applications_count === "number"
                                  ? `${job.applications_count} candidat${job.applications_count > 1 ? "s" : ""}`
                                  : "-"}
                              </td>
                              <td>
                                {job.urgent ? (
                                  <span className="jobs-badge-urgent">Urgent</span>
                                ) : (
                                  "-"
                                )}
                              </td>
                              <td>{date}</td>
                            </tr>
                          );
                        })}
                        {jobs.length === 0 && (
                          <tr>
                            <td colSpan={5}>Aucune offre créée pour le moment.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {active === "applications" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Candidatures</h1>
                <p className="dash-page-sub">
                  Suivi des candidatures par offre. (Section à compléter)
                </p>
              </div>
            </div>
          )}

          {active === "candidates" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Base candidats</h1>
                <p className="dash-page-sub">
                  Recherche et consultation de profils candidats. (Section à compléter)
                </p>
              </div>
            </div>
          )}

          {active === "activity" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Activité récente</h1>
                <p className="dash-page-sub">
                  Dernières actions et candidatures. (Section à compléter)
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
