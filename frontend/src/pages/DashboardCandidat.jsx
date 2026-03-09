import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FolderOpen, CreditCard, FileText,
  Briefcase, Image, CalendarCheck,
  LogOut, Search, TrendingUp, TrendingDown,
  Users, Bookmark, Bell, BriefcaseBusiness,
  ChevronLeft, ChevronRight, ArrowRight
} from "lucide-react";
import "../css/Dashboard.css";
import logo from "../assets/logo.svg";

/* ─── data ─────────────────────────────── */
const BARS = [42, 68, 55, 88, 60, 76, 91, 52, 80, 70, 64, 85];

const MONTHS = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"];

const GRADIENTS = [
  "linear-gradient(145deg,#1a1428 0%,#2d1b4e 100%)",
  "linear-gradient(145deg,#0f1e2a 0%,#1a3a4a 100%)",
  "linear-gradient(145deg,#1f0a0a 0%,#3d1515 100%)",
  "linear-gradient(145deg,#0a1a0f 0%,#16322a 100%)",
  "linear-gradient(145deg,#1c1408 0%,#382a10 100%)",
  "linear-gradient(145deg,#0f0f20 0%,#1e1e40 100%)",
];

const PORTFOLIO_ITEMS = [
  { id:1, title:"Brand Identity — Luxora",    desc:"Identité visuelle complète pour une maison de luxe parisienne.",      tags:["Branding","Logo"],    date:"Mar 2025", color:GRADIENTS[0] },
  { id:2, title:"App Mobile — Kora",          desc:"Expérience utilisateur pour une appli de gestion sportive.",           tags:["Mobile","UX"],        date:"Jan 2025", color:GRADIENTS[1] },
  { id:3, title:"Dashboard Analytics",        desc:"Tableau de bord interactif avec visualisations de données en temps réel.", tags:["React","UI"],        date:"Nov 2024", color:GRADIENTS[2] },
  { id:4, title:"Campagne Digital — Velvet",  desc:"Stratégie visuelle & visuels pour une campagne digitale 360°.",         tags:["Motion","Social"],    date:"Sep 2024", color:GRADIENTS[3] },
  { id:5, title:"Site E-commerce — Botanica", desc:"Design et intégration boutique premium pour une marque naturelle.",    tags:["Web","Shopify"],      date:"Juil 2024", color:GRADIENTS[4] },
  { id:6, title:"Packaging — Céleste",        desc:"Design packaging pour une gamme de cosmétiques artisanaux.",           tags:["Print","3D"],         date:"Mai 2024", color:GRADIENTS[5] },
];

const STAT_CARDS = [
  { label:"Candidatures",      value:"8",  icon:BriefcaseBusiness, trend:"+3 ce mois",      dir:"up"   },
  { label:"Entretiens",        value:"2",  icon:CalendarCheck,     trend:"+1 cette semaine", dir:"up"   },
  { label:"Offres sauvegardées", value:"5", icon:Bookmark,         trend:"Inchangé",         dir:"flat" },
  { label:"Notifications",     value:"3",  icon:Bell,              trend:"-1 aujourd'hui",   dir:"down", danger:true },
];

const STATUSES = [
  { label:"En cours",   pct:62, mod:"cr"    },
  { label:"Acceptées",  pct:25, mod:"green" },
  { label:"Refusées",   pct:13, mod:"mute"  },
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
  const navigate   = useNavigate();
  const [active,   setActive]   = useState("dashboard");
  const [collapsed,setCollapsed]= useState(false);
  const [pfTab,    setPfTab]    = useState("grid"); // "grid" | "list"

  const userEmail   = sessionStorage.getItem("userEmail")   || "vous@exemple.com";
  const userName    = (sessionStorage.getItem("userName") || userEmail.split("@")[0])
                        .charAt(0).toUpperCase() + (sessionStorage.getItem("userName") || userEmail.split("@")[0]).slice(1);

  const logout = () => {
    ["authToken","profileType","userEmail","userId","userName"].forEach(k => sessionStorage.removeItem(k));
    navigate("/connexion");
  };

  const currentLabel = MENU.find(m => m.id === active)?.label ?? "Dashboard";

  return (
    <section className="dash-section">
      <div className={`dash-layout${collapsed ? " dash-layout--collapsed" : ""}`}>

        {/* ══════ SIDEBAR ══════ */}
        <aside className="dash-sidebar">

          {/* toggle */}
          <button
            type="button"
            className="dash-toggle-btn"
            onClick={() => setCollapsed(c => !c)}
            aria-label={collapsed ? "Expand" : "Collapse"}
          >
            <ChevronLeft size={14} strokeWidth={2} />
          </button>

          {/* logo */}
          <div className="dash-logo-zone">
            <img src={logo} alt="Logo TAP" className="dash-logo-img" />
          </div>

          {/* user */}
          <div className="dash-user-block">
            <div className="dash-avatar">
              {(userName || userEmail || "?").charAt(0).toUpperCase()}
            </div>
            <div className="dash-user-text">
              <div className="dash-user-name">{userName}</div>
              <div className="dash-user-email">{userEmail}</div>
            </div>
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

          {/* footer */}
          <div className="dash-sidebar-footer">
            <button type="button" className="dash-logout" onClick={logout}>
              <LogOut size={17} strokeWidth={1.6} />
              <span className="dash-logout-label">Se déconnecter</span>
            </button>
          </div>
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
              <div className="dash-search-wrap">
                <Search size={14} color="var(--t3)" />
                <input type="search" className="dash-search" placeholder="Rechercher…" />
              </div>
              <button className="dash-topbar-btn" aria-label="Notifications">
                <Bell size={16} strokeWidth={1.6} />
              </button>
            </div>
          </div>

          {/* ── DASHBOARD ── */}
          {active === "dashboard" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">
                  Bonjour, <em>{userName}</em>
                </h1>
                <p className="dash-page-sub">
                  Voici un aperçu de votre activité · {new Date().toLocaleDateString("fr-FR", { weekday:"long", day:"numeric", month:"long" })}
                </p>
              </div>

              {/* stat cards */}
              <div className="dash-cards-row">
                {STAT_CARDS.map(({ label, value, icon: Icon, trend, dir, danger }) => (
                  <div key={label} className={`dash-card${danger ? " dash-card--danger" : ""}`}>
                    <div className="dash-card-row1">
                      <span className="dash-card-label">{label}</span>
                      <div className="dash-card-icon-wrap"><Icon size={16} /></div>
                    </div>
                    <div className="dash-card-value">{value}</div>
                    <div className={`dash-card-trend dash-card-trend--${dir === "up" ? "up" : dir === "down" ? "down" : "flat"}`}>
                      {dir === "up"   && <TrendingUp   size={13} />}
                      {dir === "down" && <TrendingDown  size={13} />}
                      {trend}
                    </div>
                  </div>
                ))}
              </div>

              {/* charts */}
              <div className="dash-grid-2">
                <div className="dash-panel dash-panel-1">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Activité mensuelle</span>
                    <span className="dash-panel-chip">12 mois</span>
                  </div>
                  <div className="dash-chart">
                    {BARS.map((h, i) => (
                      <div key={i} className="dash-bar" style={{ height:`${h}%` }} title={MONTHS[i]} />
                    ))}
                  </div>
                </div>

                <div className="dash-panel dash-panel-2">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Candidatures</span>
                    <Users size={15} color="var(--t3)" />
                  </div>
                  <div className="dash-status-list">
                    {STATUSES.map(({ label, pct, mod }) => (
                      <div className="dash-status-item" key={label}>
                        <div className="dash-status-row">
                          <span className="dash-status-name">{label}</span>
                          <span className="dash-status-pct">{pct}%</span>
                        </div>
                        <div className="dash-status-track">
                          <div className={`dash-status-bar dash-status-bar--${mod}`} style={{ width:`${pct}%` }} />
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
                {/* tab switcher */}
                <div className="portfolio-tabs">
                  <button
                    type="button"
                    className={`portfolio-tab${pfTab === "grid" ? " portfolio-tab--active" : ""}`}
                    onClick={() => setPfTab("grid")}
                  >
                    Vue Galerie
                  </button>
                  <button
                    type="button"
                    className={`portfolio-tab${pfTab === "list" ? " portfolio-tab--active" : ""}`}
                    onClick={() => setPfTab("list")}
                  >
                    Vue Détaillée
                  </button>
                </div>

                {/* GRID */}
                {pfTab === "grid" && (
                  <div className="pf-grid" key="grid">
                    {PORTFOLIO_ITEMS.map(({ id, title, desc, tags, color }) => (
                      <div className="pf-card" key={id}>
                        <div className="pf-thumb">
                          <div className="pf-thumb-bg" style={{ background: color }} />
                          <div className="pf-thumb-overlay" />
                          <span className="pf-thumb-num">0{id}</span>
                        </div>
                        <div className="pf-body">
                          <div className="pf-title">{title}</div>
                          <div className="pf-desc">{desc}</div>
                          <div className="pf-tags">
                            {tags.map(t => <span className="pf-tag" key={t}>{t}</span>)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* LIST */}
                {pfTab === "list" && (
                  <div className="pf-list" key="list">
                    {PORTFOLIO_ITEMS.map(({ id, title, desc, tags, date, color }) => (
                      <div className="pf-row" key={id}>
                        <div className="pf-row-thumb">
                          <div className="pf-row-thumb-bg" style={{ background: color }} />
                        </div>
                        <div className="pf-row-info">
                          <div className="pf-row-title">{title}</div>
                          <div className="pf-row-desc">{desc}</div>
                          <div className="pf-tags" style={{ marginTop:4 }}>
                            {tags.map(t => <span className="pf-tag" key={t}>{t}</span>)}
                          </div>
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
