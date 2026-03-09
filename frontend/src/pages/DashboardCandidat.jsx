import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FolderOpen, CreditCard, FileText,
  Briefcase, Image, CalendarCheck,
  LogOut, Search, TrendingUp, TrendingDown,
  Users, Bookmark, Bell, BriefcaseBusiness,
  ArrowRight, ChevronLeft, Settings
} from "lucide-react";
import "../css/Dashboard.css";
import logo from "../assets/logo-white.svg";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

/* ─── data ─────────────────────────────── */
const GRADIENTS = [
  "linear-gradient(145deg,#1a1428 0%,#2d1b4e 100%)",
  "linear-gradient(145deg,#0f1e2a 0%,#1a3a4a 100%)",
  "linear-gradient(145deg,#1f0a0a 0%,#3d1515 100%)",
  "linear-gradient(145deg,#0a1a0f 0%,#16322a 100%)",
  "linear-gradient(145deg,#1c1408 0%,#382a10 100%)",
  "linear-gradient(145deg,#0f0f20 0%,#1e1e40 100%)",
];

const PORTFOLIO_ITEMS = [
  { id:1, title:"Brand Identity — Luxora",    desc:"Identité visuelle complète pour une maison de luxe parisienne.",          tags:["Branding","Logo"],   date:"Mar 2025", color:GRADIENTS[0] },
  { id:2, title:"App Mobile — Kora",          desc:"Expérience utilisateur pour une appli de gestion sportive.",               tags:["Mobile","UX"],       date:"Jan 2025", color:GRADIENTS[1] },
  { id:3, title:"Dashboard Analytics",        desc:"Tableau de bord interactif avec visualisations de données en temps réel.", tags:["React","UI"],        date:"Nov 2024", color:GRADIENTS[2] },
  { id:4, title:"Campagne Digital — Velvet",  desc:"Stratégie visuelle & visuels pour une campagne digitale 360°.",            tags:["Motion","Social"],   date:"Sep 2024", color:GRADIENTS[3] },
  { id:5, title:"Site E-commerce — Botanica", desc:"Design et intégration boutique premium pour une marque naturelle.",        tags:["Web","Shopify"],     date:"Juil 2024",color:GRADIENTS[4] },
  { id:6, title:"Packaging — Céleste",        desc:"Design packaging pour une gamme de cosmétiques artisanaux.",               tags:["Print","3D"],        date:"Mai 2024", color:GRADIENTS[5] },
];

const MENU = [
  { id:"dashboard",  label:"Dashboard",    icon:LayoutDashboard },
  { id:"fichiers",   label:"Mes fichiers", icon:FolderOpen      },
  { id:"talentcard", label:"Talent Card",  icon:CreditCard      },
  { id:"cv",         label:"CV",           icon:FileText        },
  { id:"projets",    label:"Projets",      icon:Briefcase       },
  { id:"portfolio",  label:"Portfolio",    icon:Image           },
  { id:"entretiens", label:"Entretiens",   icon:CalendarCheck   },
];

const PAGE_CONTENT = {
  fichiers:   "Retrouvez tous vos documents : CV, lettres de motivation, pièces jointes. Organisez et partagez en un clic.",
  talentcard: "Votre Talent Card est votre vitrine professionnelle. Mettez-la à jour pour maximiser votre visibilité.",
  cv:         "Gérez plusieurs versions de CV, activez celle de votre choix et consultez les statistiques en temps réel.",
  projets:    "Répertoriez vos projets et réalisations. Chaque entrée renforce automatiquement votre profil TAP.",
  entretiens: "Historique de vos entretiens passés, prochaines étapes et rappels automatiques pour ne rien manquer.",
};

/* ─── component ────────────────────────── */
export default function DashboardCandidat() {
  const navigate = useNavigate();
  const [active,      setActive]      = useState("dashboard");
  const [pfTab,       setPfTab]       = useState("grid");
  const [collapsed,   setCollapsed]   = useState(false);
  const [showNotif,   setShowNotif]   = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [stats,       setStats]       = useState({
    applications: null,
    interviews: null,
    savedOffers: null,
    notifications: null,
    statusPending: null,
    statusAccepted: null,
    statusRefused: null,
  });

  const notifRef   = useRef(null);
  const profileRef = useRef(null);

  const userEmail = sessionStorage.getItem("userEmail") || "vous@exemple.com";
  const rawName   = sessionStorage.getItem("userName")  || userEmail.split("@")[0];
  const userName  = rawName.charAt(0).toUpperCase() + rawName.slice(1);
  const userId    = sessionStorage.getItem("userId");

  const logout = () => {
    ["authToken","profileType","userEmail","userId","userName"].forEach(k => sessionStorage.removeItem(k));
    navigate("/connexion");
  };

  /* close dropdowns on outside click */
  useEffect(() => {
    const fn = (e) => {
      if (notifRef.current   && !notifRef.current.contains(e.target))   setShowNotif(false);
      if (profileRef.current && !profileRef.current.contains(e.target)) setShowProfile(false);
    };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, []);

  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();

    const loadStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => null);
        if (!res.ok || !data) return;

        setStats({
          applications: data.applications ?? 0,
          interviews: data.interviews ?? 0,
          savedOffers: data.savedOffers ?? 0,
          notifications: data.notifications ?? 0,
          statusPending: data.statusPending ?? 0,
          statusAccepted: data.statusAccepted ?? 0,
          statusRefused: data.statusRefused ?? 0,
        });
      } catch (e) {
        if (e.name === "AbortError") return;
      }
    };

    loadStats();

    return () => controller.abort();
  }, [userId]);

  const currentLabel = MENU.find(m => m.id === active)?.label ?? "Dashboard";
  const unreadCount  = stats.notifications ?? 0;

  const totalStatus =
    (stats.statusPending  ?? 0) +
    (stats.statusAccepted ?? 0) +
    (stats.statusRefused  ?? 0);

  const statusChart = [
    {
      key: "pending",
      label: "En cours",
      mod: "cr",
      count: stats.statusPending ?? 0,
      pct: totalStatus ? Math.round(((stats.statusPending ?? 0) / totalStatus) * 100) : 0,
    },
    {
      key: "accepted",
      label: "Acceptées",
      mod: "green",
      count: stats.statusAccepted ?? 0,
      pct: totalStatus ? Math.round(((stats.statusAccepted ?? 0) / totalStatus) * 100) : 0,
    },
    {
      key: "refused",
      label: "Refusées",
      mod: "mute",
      count: stats.statusRefused ?? 0,
      pct: totalStatus ? Math.round(((stats.statusRefused ?? 0) / totalStatus) * 100) : 0,
    },
  ];

  const statCards = [
    { label:"Candidatures",        value: stats.applications,  icon:BriefcaseBusiness, trend:"+3 ce mois",        dir:"up"   },
    { label:"Entretiens",          value: stats.interviews,    icon:CalendarCheck,     trend:"+1 cette semaine",  dir:"up"   },
    { label:"Offres sauvegardées", value: stats.savedOffers,   icon:Bookmark,          trend:"Inchangé",          dir:"flat" },
    { label:"Notifications",       value: stats.notifications, icon:Bell,              trend:"Mises à jour",      dir:"flat", danger:true },
  ];

  const handleSidebarClick = () => {
    if (collapsed) {
      setCollapsed(false);
    }
  };

  return (
    <section className="dash-section">
      <div className={`dash-layout${collapsed ? " dash-layout--collapsed" : ""}`}>

        {/* ══════ SIDEBAR ══════ */}
        <aside className="dash-sidebar" onClick={handleSidebarClick}>

          {/* logo */}
          <div className="dash-logo-zone">
            <img src={logo} alt="Logo TAP" className="dash-logo-img" />
          </div>

          {/* nav */}
          <nav className="dash-nav">
            <div className="dash-nav-section-label">Navigation</div>
            {MENU.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                data-label={label}
                className={`dash-menu-item${active === id ? " dash-menu-item--active" : ""}`}
                onClick={() => setActive(id)}
              >
                <span className="dash-menu-icon">
                  <Icon size={18} strokeWidth={active === id ? 2 : 1.6} />
                </span>
                <span className="dash-menu-label">{label}</span>
              </button>
            ))}
          </nav>

          {/* footer logout — toujours visible (icône seule si collapsed) */}
          <div className="dash-sidebar-footer">
            <button type="button" className="dash-logout" onClick={logout} title="Se déconnecter">
              <LogOut size={17} strokeWidth={1.6} />
              <span className="dash-logout-label">Se déconnecter</span>
            </button>
          </div>

          {/* ── CHEVRON — affiché uniquement quand la sidebar est ouverte ── */}
          {!collapsed && (
            <div
              className="dash-collapse-btn"
              onClick={() => setCollapsed(c => !c)}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === "Enter" && setCollapsed(c => !c)}
              aria-label={collapsed ? "Ouvrir la sidebar" : "Fermer la sidebar"}
            >
              <ChevronLeft
                size={16}
                strokeWidth={2.5}
                className="dash-collapse-icon"
              />
            </div>
          )}

        </aside>

        {/* ══════ MAIN ══════ */}
        <main className="dash-main">

          {/* topbar */}
          <div className="dash-topbar">
            <div className="dash-topbar-left">
              <div className="dash-breadcrumb">
                <span>Espace</span>
                <span className="dash-breadcrumb-sep">›</span>
                <span className="dash-breadcrumb-current">{currentLabel}</span>
              </div>
            </div>

            <div className="dash-topbar-right">

              {/* search */}
              <div className="dash-search-wrap">
                <Search size={14} color="var(--t3)" />
                <input type="search" className="dash-search" placeholder="Rechercher…" />
              </div>

              {/* ── BELL — icône pure, pas de bouton ── */}
              <div className="dash-notif-wrap" ref={notifRef}>
                <div
                  className="dash-notif-trigger"
                  onClick={() => { setShowNotif(v => !v); setShowProfile(false); }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => e.key === "Enter" && setShowNotif(v => !v)}
                >
                  <Bell size={18} strokeWidth={1.6} />
                  {unreadCount > 0 && <span className="dash-notif-badge">{unreadCount}</span>}
                </div>

                {showNotif && (
                  <div className="dash-notif-dropdown">
                    <div className="dash-notif-header">
                      <span>Notifications</span>
                      <span className="dash-notif-count">{unreadCount} non lues</span>
                    </div>
                    <div className="dash-notif-item dash-notif-item--unread">
                      <div className="dash-notif-dot" />
                      <div className="dash-notif-body">
                        <p className="dash-notif-text">
                          Vous avez {unreadCount ?? 0} notification(s) liée(s) à votre activité récente.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* ── AVATAR PROFIL topbar — hover dropdown ── */}
              <div className="dash-profile-wrap" ref={profileRef}>
                <div
                  className={`dash-topbar-avatar${showProfile ? " dash-topbar-avatar--active" : ""}`}
                  onClick={() => { setShowProfile(v => !v); setShowNotif(false); }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => e.key === "Enter" && setShowProfile(v => !v)}
                  aria-label="Profil"
                >
                  {userName.charAt(0).toUpperCase()}
                </div>

                {showProfile && (
                  <div className="dash-profile-dropdown">
                    <div className="dash-profile-header">
                      <div className="dash-profile-avatar-lg">
                        {userName.charAt(0).toUpperCase()}
                      </div>
                      <div className="dash-profile-info">
                        <span className="dash-profile-name">{userName}</span>
                        <span className="dash-profile-email">{userEmail}</span>
                      </div>
                    </div>
                    <div className="dash-profile-divider" />
                    <button className="dash-profile-action" type="button">
                      <Settings size={14} strokeWidth={1.6} />
                      Paramètres
                    </button>
                    <button className="dash-profile-action dash-profile-action--logout" type="button" onClick={logout}>
                      <LogOut size={14} strokeWidth={1.6} />
                      Se déconnecter
                    </button>
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* ── DASHBOARD ── */}
          {active === "dashboard" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Bonjour, <em>{userName}</em></h1>
                <p className="dash-page-sub">
                  Voici un aperçu de votre activité · {new Date().toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long"})}
                </p>
              </div>

              <div className="dash-cards-row">
                {statCards.map(({ label, value, icon: Icon, trend, dir, danger }) => (
                  <div key={label} className={`dash-card${danger ? " dash-card--danger" : ""}`}>
                    <div className="dash-card-row1">
                      <span className="dash-card-label">{label}</span>
                      <div className="dash-card-icon-wrap"><Icon size={16} /></div>
                    </div>
                    <div className="dash-card-value">{value ?? "—"}</div>
                    <div className={`dash-card-trend dash-card-trend--${dir === "up" ? "up" : dir === "down" ? "down" : "flat"}`}>
                      {dir === "up"   && <TrendingUp   size={13} />}
                      {dir === "down" && <TrendingDown  size={13} />}
                      {trend}
                    </div>
                  </div>
                ))}
              </div>

              <div className="dash-grid-2">
                <div className="dash-panel dash-panel-1">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">État des candidatures</span>
                    <span className="dash-panel-chip">En temps réel</span>
                  </div>
                  <div className="dash-chart">
                    {statusChart.map(({ key, pct, label }) => (
                      <div
                        key={key}
                        className="dash-bar"
                        style={{ height: `${pct || 0}%` }}
                        title={`${label} · ${pct || 0}%`}
                      />
                    ))}
                  </div>
                </div>

                <div className="dash-panel dash-panel-2">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Candidatures par statut</span>
                    <Users size={15} color="var(--t3)" />
                  </div>
                  <div className="dash-status-list">
                    {statusChart.map(({ key, label, pct, mod, count }) => (
                      <div className="dash-status-item" key={key}>
                        <div className="dash-status-row">
                          <span className="dash-status-name">{label}</span>
                          <span className="dash-status-pct">
                            {pct}% · {count} candidatures
                          </span>
                        </div>
                        <div className="dash-status-track">
                          <div
                            className={`dash-status-bar dash-status-bar--${mod}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── PORTFOLIO ── */}
          {active === "portfolio" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Portfolio</h1>
                <p className="dash-page-sub">Vos réalisations et projets · {PORTFOLIO_ITEMS.length} travaux</p>
              </div>
              <div className="portfolio-shell">
                <div className="portfolio-tabs">
                  <button type="button" className={`portfolio-tab${pfTab==="grid"?" portfolio-tab--active":""}`} onClick={()=>setPfTab("grid")}>Vue Galerie</button>
                  <button type="button" className={`portfolio-tab${pfTab==="list"?" portfolio-tab--active":""}`} onClick={()=>setPfTab("list")}>Vue Détaillée</button>
                </div>

                {pfTab === "grid" && (
                  <div className="pf-grid" key="grid">
                    {PORTFOLIO_ITEMS.map(({ id, title, desc, tags, color }) => (
                      <div className="pf-card" key={id}>
                        <div className="pf-thumb">
                          <div className="pf-thumb-bg" style={{ background:color }} />
                          <div className="pf-thumb-overlay" />
                          <span className="pf-thumb-num">0{id}</span>
                        </div>
                        <div className="pf-body">
                          <div className="pf-title">{title}</div>
                          <div className="pf-desc">{desc}</div>
                          <div className="pf-tags">{tags.map(t=><span className="pf-tag" key={t}>{t}</span>)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {pfTab === "list" && (
                  <div className="pf-list" key="list">
                    {PORTFOLIO_ITEMS.map(({ id, title, desc, tags, date, color }) => (
                      <div className="pf-row" key={id}>
                        <div className="pf-row-thumb"><div className="pf-row-thumb-bg" style={{ background:color }} /></div>
                        <div className="pf-row-info">
                          <div className="pf-row-title">{title}</div>
                          <div className="pf-row-desc">{desc}</div>
                          <div className="pf-tags" style={{marginTop:4}}>{tags.map(t=><span className="pf-tag" key={t}>{t}</span>)}</div>
                        </div>
                        <div className="pf-row-meta">
                          <span className="pf-row-date">{date}</span>
                          <ArrowRight size={15} className="pf-row-arrow" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── OTHER PAGES ── */}
          {active !== "dashboard" && active !== "portfolio" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">{currentLabel}</h1>
                <p className="dash-page-sub">Gérez et organisez votre espace personnel</p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  <p>{PAGE_CONTENT[active] || "Section en cours de construction."}</p>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </section>
  );
}
