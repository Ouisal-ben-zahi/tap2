
import React, { useState, useEffect } from "react";
import "../css/Dashboard.css";
import {
  LayoutDashboard,
  BriefcaseBusiness,
  Users,
  BarChart2,
  Bell,
  Search,
  LogOut,
  Award,
  Zap,
  AlertTriangle,
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
  const [overview, setOverview] = useState(null);
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

  useEffect(() => {
    if (active !== "overview") return;
    const userId = sessionStorage.getItem("userId");
    if (!userId) return;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/recruteur/${userId}/overview`);
        const data = await res.json().catch(() => null);
        if (res.ok && data) {
          setOverview(data);
        }
      } catch {
        // ignore
      }
    })();
  }, [active]);

  useEffect(() => {
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
                  Synthèse de vos offres, candidatures et alertes en temps réel.
                </p>
              </div>

              {/* KPI CARDS */}
              <div className="dash-cards-row">
                <div className="dash-card recruiter-kpi-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Jobs postés</span>
                    <div className="dash-card-icon-wrap">
                      <BriefcaseBusiness size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {overview?.totalJobs ?? "—"}
                  </div>
                </div>

                <div className="dash-card recruiter-kpi-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Candidats uniques</span>
                    <div className="dash-card-icon-wrap">
                      <Users size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {overview?.totalCandidates ?? "—"}
                  </div>
                </div>

                <div className="dash-card recruiter-kpi-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Candidatures</span>
                    <div className="dash-card-icon-wrap">
                      <LayoutDashboard size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {overview?.totalApplications ?? "—"}
                  </div>
                </div>

                <div className="dash-card recruiter-kpi-card">
                  <div className="dash-card-row1">
                    <span className="dash-card-label">Offres urgentes</span>
                    <div className="dash-card-icon-wrap">
                      <BarChart2 size={16} />
                    </div>
                  </div>
                  <div className="dash-card-value">
                    {overview?.urgentJobs ?? "—"}
                  </div>
                </div>
              </div>

              {/* GRAPHIQUES + ALERTES */}
              <div className="dash-grid-2">
                <div className="dash-panel dash-panel-1 recruiter-insight-panel">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">
                      Candidatures par offre
                    </span>
                    <Award size={14} color="var(--gold)" />
                  </div>
                  <div className="dash-chart">
                    {overview?.applicationsPerJob &&
                    overview.applicationsPerJob.length > 0 ? (
                      overview.applicationsPerJob.slice(0, 8).map((item) => {
                        const max = Math.max(
                          ...overview.applicationsPerJob.map(
                            (x) => x.value || 0
                          )
                        );
                        const height = max > 0 ? (item.value / max) * 100 : 0;
                        return (
                          <div
                            key={item.jobId}
                            className="dash-chart-bar-wrap"
                          >
                            <div
                              className="dash-bar"
                              style={{
                                height: `${Math.max(8, height)}%`,
                              }}
                            />
                            <div className="dash-bar-label">
                              {item.title.length > 10
                                ? `${item.title.slice(0, 9)}…`
                                : item.title}
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div style={{ fontSize: 12, color: "var(--t3)" }}>
                        Aucune candidature pour l’instant.
                      </div>
                    )}
                  </div>
                </div>

                <div className="dash-panel dash-panel-2 recruiter-insight-panel">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Jobs par catégorie</span>
                    <Zap size={14} color="var(--gold)" />
                  </div>
                  <div className="dash-status-list">
                    {overview?.jobsPerCategory &&
                    overview.jobsPerCategory.length > 0 ? (
                      overview.jobsPerCategory.map((cat) => {
                        const total = overview.totalJobs || 1;
                        const pct = Math.round((cat.value / total) * 100);
                        return (
                          <div
                            key={cat.label}
                            className="dash-status-item"
                          >
                            <div className="dash-status-row">
                              <span className="dash-status-name">
                                {cat.label}
                              </span>
                              <span className="dash-status-pct">
                                {cat.value} ({pct}%)
                              </span>
                            </div>
                            <div className="dash-status-track">
                              <div
                                className="dash-status-bar dash-status-bar--cr"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <p style={{ fontSize: 12, color: "var(--t3)" }}>
                        Aucune offre publiée pour le moment.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* DERNIÈRES CANDIDATURES + ALERTES */}
              <div className="dash-grid-2" style={{ marginTop: 16 }}>
                <div className="dash-recent-panel">
                  <div className="dash-recent-head">
                    <span className="dash-recent-title">
                      Dernières candidatures
                    </span>
                  </div>
                  {overview?.recentApplications &&
                  overview.recentApplications.length > 0 ? (
                    overview.recentApplications.map((app) => {
                      const st = (app.status || "").toUpperCase();
                      const label =
                        st === "ACCEPTEE"
                          ? "Acceptée"
                          : st === "REFUSEE"
                          ? "Refusée"
                          : "En cours";
                      const pillClass =
                        st === "ACCEPTEE"
                          ? "accepted"
                          : st === "REFUSEE"
                          ? "refused"
                          : "pending";
                      const date = app.validatedAt
                        ? new Date(app.validatedAt).toLocaleDateString(
                            "fr-FR",
                            { day: "2-digit", month: "short" }
                          )
                        : "-";
                      return (
                        <div className="dash-recent-row" key={app.id}>
                          <div>
                            <div className="dash-recent-title-job">
                              {app.jobTitle || "Offre"}
                            </div>
                            {app.candidateName && (
                              <div className="dash-recent-company">
                                {app.candidateName}
                              </div>
                            )}
                          </div>
                          <span
                            className={`dash-status-pill dash-status-pill--${pillClass}`}
                          >
                            {label}
                          </span>
                          <div className="dash-recent-date">{date}</div>
                        </div>
                      );
                    })
                  ) : (
                    <p
                      style={{
                        fontSize: 13,
                        color: "var(--t3)",
                      }}
                    >
                      Aucune candidature récente.
                    </p>
                  )}
                </div>

                <div className="dash-panel recruiter-insight-panel">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Vue synthétique</span>
                    <Award size={14} color="var(--gold)" />
                  </div>
                  <div className="dash-status-list">
                    <div className="dash-status-item">
                      <div className="dash-status-row">
                        <span className="dash-status-name">Moyenne de candidatures par offre</span>
                        <span className="dash-status-pct">
                          {overview?.totalJobs
                            ? ((overview.totalApplications || 0) / overview.totalJobs).toFixed(1)
                            : "—"}
                        </span>
                      </div>
                      <div className="dash-status-track">
                        <div
                          className="dash-status-bar dash-status-bar--cr"
                          style={{
                            width: `${
                              overview?.totalJobs
                                ? Math.min(
                                    100,
                                    (((overview.totalApplications || 0) / overview.totalJobs) /
                                      10) *
                                      100
                                  )
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="dash-status-item">
                      <div className="dash-status-row">
                        <span className="dash-status-name">Part d’offres urgentes</span>
                        <span className="dash-status-pct">
                          {overview?.totalJobs
                            ? `${Math.round(
                                ((overview.urgentJobs || 0) / overview.totalJobs) * 100
                              )}%`
                            : "—"}
                        </span>
                      </div>
                      <div className="dash-status-track">
                        <div
                          className="dash-status-bar dash-status-bar--green"
                          style={{
                            width: `${
                              overview?.totalJobs
                                ? Math.round(
                                    ((overview.urgentJobs || 0) / overview.totalJobs) * 100
                                  )
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="dash-status-item">
                      <div className="dash-status-row">
                        <span className="dash-status-name">Ratio candidats / candidatures</span>
                        <span className="dash-status-pct">
                          {overview?.totalApplications
                            ? (overview.totalCandidates || 0) > 0
                              ? (
                                  overview.totalApplications / (overview.totalCandidates || 1)
                                ).toFixed(1)
                              : "—"
                            : "—"}
                        </span>
                      </div>
                      <div className="dash-status-track">
                        <div
                          className="dash-status-bar dash-status-bar--mute"
                          style={{
                            width: `${
                              overview?.totalApplications && overview.totalCandidates
                                ? Math.min(
                                    100,
                                    (
                                      overview.totalApplications /
                                      (overview.totalCandidates || 1) /
                                      10
                                    ) * 100
                                  )
                                : 0
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="dash-panel recruiter-alerts-panel">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Alertes recruteur</span>
                    <AlertTriangle size={14} color="var(--gold)" />
                  </div>
                  {overview?.alerts && overview.alerts.length > 0 ? (
                    <div className="dash-anomaly-list">
                      {overview.alerts.map((a) => (
                        <div
                          key={a.type}
                          className="dash-anomaly-item dash-anomaly-item--bad"
                        >
                          <div className="dash-anomaly-dot" />
                          <span>{a.message}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: 13, color: "var(--t3)" }}>
                      Aucune alerte critique pour le moment.
                    </p>
                  )}
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
                  <div className="dash-section-card">
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
                  </div>
                )}

                {/* Table des offres */}
                <div className="dash-section-card dash-section-card--flush" style={{ marginTop: 16 }}>
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
