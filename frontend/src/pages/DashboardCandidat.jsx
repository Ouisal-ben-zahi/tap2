import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../css/Dashboard.css";

function DashboardCandidat() {
  const navigate = useNavigate();
  const [active, setActive] = useState("bienvenue");

  const profileType = sessionStorage.getItem("profileType") || "candidat";
  const userEmail = sessionStorage.getItem("userEmail") || "vous@exemple.com";

  const handleLogout = () => {
    sessionStorage.removeItem("authToken");
    sessionStorage.removeItem("profileType");
    sessionStorage.removeItem("userEmail");
    sessionStorage.removeItem("userId");
    navigate("/connexion");
  };

  const menuItems = [
    { id: "bienvenue", label: "Bienvenue" },
    { id: "fichiers", label: "Mes fichiers" },
    { id: "talentcard", label: "Talent Card" },
    { id: "cv", label: "CV" },
    { id: "projects", label: "Projects" },
    { id: "portfolio", label: "Portfolio" },
    { id: "entretiens", label: "Entretiens" },
    { id: "portfolio2", label: "Portfolio 2" },
  ];

  const renderContent = () => {
    switch (active) {
      case "fichiers":
        return "Ici vous verrez tous vos fichiers (CV, portfolio, documents…).";
      case "talentcard":
        return "Vue et mise à jour de votre Talent Card.";
      case "cv":
        return "Gestion de vos versions de CV.";
      case "projects":
        return "Liste de vos projets et réalisations.";
      case "portfolio":
        return "Aperçu de votre portfolio principal.";
      case "entretiens":
        return "Historique et prochaines étapes d’entretiens.";
      case "portfolio2":
        return "Deuxième vue de portfolio (expérimentale).";
      case "bienvenue":
      default:
        return "Bienvenue sur votre tableau de bord candidat TAP.";
    }
  };

  return (
    <section className="dash-section">
      <div className="dash-layout">
        <aside className="dash-sidebar">
          <div className="dash-sidebar-header">
            <div className="dash-avatar">
              {(userEmail || "?").charAt(0).toUpperCase()}
            </div>
            <div className="dash-user-info">
              <div className="dash-user-role">
                Tableau de bord candidat
              </div>
              <div className="dash-user-email">{userEmail}</div>
            </div>
          </div>

          <nav className="dash-menu">
            {menuItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className={
                  "dash-menu-item" +
                  (active === item.id ? " dash-menu-item--active" : "")
                }
                onClick={() => setActive(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <button
            type="button"
            className="dash-logout"
            onClick={handleLogout}
          >
            Se déconnecter
          </button>
        </aside>

        <main className="dash-main">
          <header className="dash-main-header">
            <div className="dash-main-header-top">
              <h1 className="dash-main-title">
                {active === "bienvenue"
                  ? "Bienvenue !"
                  : menuItems.find((m) => m.id === active)?.label}
              </h1>
              <input
                type="search"
                className="dash-search"
                placeholder="Rechercher..."
              />
            </div>
            <p className="dash-main-subtitle">
              Profil : {profileType === "recruteur" ? "Recruteur" : "Candidat"}
            </p>
          </header>

          <section className="dash-main-content">
            {active === "bienvenue" ? (
              <>
                <div className="dash-cards-row">
                  <div className="dash-card">
                    <div className="dash-card-label">Candidatures envoyées</div>
                    <div className="dash-card-value">8</div>
                  </div>
                  <div className="dash-card">
                    <div className="dash-card-label">Entretiens à venir</div>
                    <div className="dash-card-value">2</div>
                  </div>
                  <div className="dash-card">
                    <div className="dash-card-label">Offres sauvegardées</div>
                    <div className="dash-card-value">5</div>
                  </div>
                  <div className="dash-card">
                    <div className="dash-card-label">Notifications non lues</div>
                    <div className="dash-card-value">3</div>
                  </div>
                </div>

                <div className="dash-grid-row">
                  <div className="dash-panel dash-panel-large">
                    <div className="dash-panel-title">Activité des 6 derniers mois</div>
                    <div className="dash-fake-chart" />
                  </div>
                  <div className="dash-panel dash-panel-side">
                    <div className="dash-panel-title">Statut des candidatures</div>
                    <ul className="dash-status-list">
                      <li>
                        <span>En cours</span>
                        <span className="dash-status-bar dash-status-bar--primary" />
                      </li>
                      <li>
                        <span>Acceptées</span>
                        <span className="dash-status-bar dash-status-bar--success" />
                      </li>
                      <li>
                        <span>Refusées</span>
                        <span className="dash-status-bar dash-status-bar--muted" />
                      </li>
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <div className="dash-panel">
                <p>{renderContent()}</p>
              </div>
            )}
          </section>
        </main>
      </div>
    </section>
  );
}

export default DashboardCandidat;

