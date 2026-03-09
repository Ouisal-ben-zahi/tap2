import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FolderOpen, CreditCard, FileText,
  Briefcase, Image, CalendarCheck, Layers,
  LogOut, Search, TrendingUp, TrendingDown,
  Users, Bookmark, Bell, BriefcaseBusiness,
  ChevronLeft, ChevronRight
} from "lucide-react";
import "../css/Dashboard.css";

/* ── mock bar heights for fake chart ── */
const BARS = [55, 72, 48, 85, 63, 91, 70, 58, 80, 67, 74, 88];

function DashboardCandidat() {
  const navigate  = useNavigate();
  const [active, setActive] = useState("bienvenue");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const profileType = sessionStorage.getItem("profileType") || "candidat";
  const userEmail   = sessionStorage.getItem("userEmail")   || "vous@exemple.com";
  const userName    = sessionStorage.getItem("userName")    || userEmail.split("@")[0];

  const handleLogout = () => {
    ["authToken","profileType","userEmail","userId","userName"]
      .forEach(k => sessionStorage.removeItem(k));
    navigate("/connexion");
  };

  /* ── nav items ── */
  const menuItems = [
    { id: "bienvenue",  label: "Tableau de bord", icon: LayoutDashboard },
    { id: "fichiers",   label: "Mes fichiers",    icon: FolderOpen       },
    { id: "talentcard", label: "Talent Card",     icon: CreditCard       },
    { id: "cv",         label: "CV",              icon: FileText         },
    { id: "projects",   label: "Projets",         icon: Briefcase        },
    { id: "portfolio",  label: "Portfolio",       icon: Image            },
    { id: "entretiens", label: "Entretiens",      icon: CalendarCheck    },
    { id: "portfolio2", label: "Portfolio  II",   icon: Layers           },
  ];

  /* ── page title helper ── */
  const pageTitle = () => {
    if (active === "bienvenue") return <>Bienvenue, <span>{userName} !</span></>;
    return menuItems.find(m => m.id === active)?.label;
  };

  /* ── stat cards data ── */
  const cards = [
    {
      label: "Candidatures envoyées",
      value: "8",
      icon: BriefcaseBusiness,
      trend: "+3 ce mois",
      up: true,
    },
    {
      label: "Entretiens à venir",
      value: "2",
      icon: CalendarCheck,
      trend: "+1 cette semaine",
      up: true,
    },
    {
      label: "Offres sauvegardées",
      value: "5",
      icon: Bookmark,
      trend: "inchangé",
      up: null,
    },
    {
      label: "Notifications non lues",
      value: "3",
      icon: Bell,
      trend: "-1 aujourd'hui",
      up: false,
      danger: true,
    },
  ];

  /* ── status items ── */
  const statuses = [
    { label: "Candidatures en cours", pct: 62, fill: "red"   },
    { label: "Candidatures acceptées", pct: 25, fill: "green" },
    { label: "Candidatures refusées",  pct: 13, fill: "muted" },
  ];

  return (
    <section className="dash-section">
      <div className={`dash-layout${sidebarCollapsed ? " dash-layout--collapsed" : ""}`}>

        {/* ════ SIDEBAR ════ */}
        <aside className={`dash-sidebar${sidebarCollapsed ? " dash-sidebar--collapsed" : ""}`}>
          {/* user block + toggle */}
          <div className="dash-sidebar-header">
            <button
              type="button"
              className="dash-toggle-btn"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              aria-label={sidebarCollapsed ? "Ouvrir le menu" : "Réduire le menu"}
            >
              {sidebarCollapsed ? (
                <ChevronRight size={18} strokeWidth={2.2} color="#fee2e2" />
              ) : (
                <ChevronLeft size={18} strokeWidth={2.2} color="#fee2e2" />
              )}
            </button>
            <div className="dash-user-block">
              <div className="dash-avatar">
                {(userEmail || "?").charAt(0).toUpperCase()}
              </div>
              {!sidebarCollapsed && (
                <div className="dash-user-info">
                  <span className="dash-user-role">
                    {profileType === "recruteur" ? "Recruteur" : "Candidat"}
                  </span>
                  <span className="dash-user-email">{userEmail}</span>
                </div>
              )}
            </div>
          </div>

          {/* navigation */}
          <nav className="dash-menu">
            {menuItems.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                className={`dash-menu-item${active === id ? " dash-menu-item--active" : ""}`}
                onClick={() => setActive(id)}
              >
                <Icon size={14} strokeWidth={active === id ? 2.2 : 1.7} />
                <span className="dash-menu-label">{label}</span>
              </button>
            ))}
          </nav>

          {/* logout */}
          <button type="button" className="dash-logout" onClick={handleLogout}>
            <LogOut size={13} strokeWidth={1.8} />
            <span className="dash-logout-label">Se déconnecter</span>
          </button>
        </aside>

        {/* ════ MAIN ════ */}
        <main className="dash-main">

          {/* header */}
          <header className="dash-main-header">
            <div>
              <h1 className="dash-main-title">{pageTitle()}</h1>
              <p className="dash-main-subtitle">
                Profil · {profileType === "recruteur" ? "Recruteur" : "Candidat TAP"}
              </p>
            </div>

            <div className="dash-search-wrap">
              <Search size={13} color="var(--text-muted)" />
              <input
                type="search"
                className="dash-search"
                placeholder="Rechercher…"
              />
            </div>
          </header>

          {/* ── dashboard home ── */}
          {active === "bienvenue" ? (
            <>
              {/* stat cards */}
              <div className="dash-cards-row">
                {cards.map(({ label, value, icon: Icon, trend, up, danger }) => (
                  <div key={label} className={`dash-card${danger ? " dash-card--danger" : ""}`}>
                    <div className="dash-card-top">
                      <span className="dash-card-label">{label}</span>
                      <div className="dash-card-icon">
                        <Icon size={14} />
                      </div>
                    </div>
                    <div className="dash-card-value">{value}</div>
                    <div className={`dash-card-trend ${up === true ? "dash-card-trend--up" : up === false ? "dash-card-trend--down" : ""}`}
                         style={up === null ? { color: "var(--text-muted)" } : {}}>
                      {up === true  && <TrendingUp  size={11} />}
                      {up === false && <TrendingDown size={11} />}
                      {trend}
                    </div>
                  </div>
                ))}
              </div>

              {/* chart row */}
              <div className="dash-grid-row">
                {/* activity chart */}
                <div className="dash-panel dash-panel-large">
                  <div className="dash-panel-header">
                    <span className="dash-panel-title">Activité — 12 derniers mois</span>
                    <span className="dash-panel-badge">Live</span>
                  </div>
                  <div className="dash-fake-chart">
                    {BARS.map((h, i) => (
                      <div
                        key={i}
                        className="dash-fake-bar"
                        style={{ height: `${h}%` }}
                      />
                    ))}
                  </div>
                </div>

                {/* status panel */}
                <div className="dash-panel dash-panel-side">
                  <div className="dash-panel-header">
                    <span className="dash-panel-title">Statut candidatures</span>
                    <Users size={14} color="var(--text-muted)" />
                  </div>
                  <ul className="dash-status-list">
                    {statuses.map(({ label, pct, fill }) => (
                      <li key={label}>
                        <div className="dash-status-row">
                          <span className="dash-status-label">{label}</span>
                          <span className="dash-status-pct">{pct}%</span>
                        </div>
                        <div className="dash-status-track">
                          <div
                            className={`dash-status-fill dash-status-fill--${fill}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          ) : (
            /* ── inner page ── */
            <div className="dash-panel">
              <div className="dash-panel-header">
                <span className="dash-panel-title">
                  {menuItems.find(m => m.id === active)?.label}
                </span>
                <span className="dash-panel-badge">Section</span>
              </div>
              <p className="dash-panel-content">
                {renderContent(active)}
              </p>
            </div>
          )}
        </main>
      </div>
    </section>
  );
}

/* ── content map ── */
function renderContent(active) {
  const map = {
    fichiers:   "Ici vous retrouvez tous vos documents : CV, portfolio, lettres de motivation et pièces jointes uploadées.",
    talentcard: "Consultez et mettez à jour votre Talent Card pour maximiser votre visibilité auprès des recruteurs.",
    cv:         "Gérez toutes vos versions de CV, activez celle de votre choix et suivez les consultations.",
    projects:   "Listez vos projets et réalisations clés. Chaque entrée enrichit votre profil TAP.",
    portfolio:  "Votre portfolio principal : images, liens, descriptions. Présentez votre meilleur travail.",
    entretiens: "Historique complet de vos entretiens passés et prochaines étapes planifiées.",
    portfolio2: "Espace portfolio alternatif — idéal pour segmenter vos travaux par thématique.",
  };
  return map[active] || "";
}

export default DashboardCandidat;
