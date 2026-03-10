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
import "../css/Contact.css";

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

const MENU = [
  { id:"dashboard",  label:"Dashboard",    icon:LayoutDashboard },
  { id:"fichiers",   label:"Bienvenue",    icon:FolderOpen      },
  { id:"talentcard", label:"Talent Card",  icon:CreditCard      },
  { id:"cv",         label:"Curriculum Vitae", icon:FileText    },
  { id:"projets",    label:"Projets",      icon:Briefcase       },
  { id:"candidatures", label:"Mes candidatures", icon:BriefcaseBusiness },
  { id:"portfolio",  label:"Portfolio",    icon:Image           },
  { id:"entretiens", label:"Entretiens",   icon:CalendarCheck   },
];

const PAGE_CONTENT = {
  fichiers:   "Retrouvez tous vos documents : CV, lettres de motivation, pièces jointes. Organisez et partagez en un clic.",
  talentcard: "Votre Talent Card est votre vitrine professionnelle. Mettez-la à jour pour maximiser votre visibilité.",
  cv:         "Gérez plusieurs versions de CV, activez celle de votre choix et consultez les statistiques en temps réel.",
  projets:    "Répertoriez vos projets et réalisations. Chaque entrée renforce automatiquement votre profil TAP.",
  candidatures: "Consultez l’historique de toutes vos candidatures, leur statut (en cours, acceptée, refusée) et les détails associés.",
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
  const [portfolio,   setPortfolio]    = useState([]);
  const [portfolioShort, setPortfolioShort] = useState([]);
  const [portfolioLong,  setPortfolioLong]  = useState([]);
  const [applications,setApplications] = useState([]);
  const [cvFiles,     setCvFiles]      = useState([]);
  const [talentcardFiles, setTalentcardFiles] = useState([]);
  // état du wizard Talent Card (section Bienvenue)
  const [currentWizardStep, setCurrentWizardStep] = useState(1);
  const [cvFile, setCvFile] = useState(null);
  const [imgFile, setImgFile] = useState(null);
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [otherLinks, setOtherLinks] = useState([]);
  const [targetPosition, setTargetPosition] = useState("");
  const [targetCountry, setTargetCountry] = useState("");
  const [pretARelocater, setPretARelocater] = useState("");
  const [constraints, setConstraints] = useState("");
  const [searchCriteria, setSearchCriteria] = useState("");
  const [nationality, setNationality] = useState("");
  const [locationCountry, setLocationCountry] = useState("");
  const [seniorityLevel, setSeniorityLevel] = useState("");
  const [disponibilite, setDisponibilite] = useState("");
  const [typeContrat, setTypeContrat] = useState([]);
  const [salaireMinimum, setSalaireMinimum] = useState("");
  const [domaineActivite, setDomaineActivite] = useState("");
  const [talentCardLang, setTalentCardLang] = useState(
    () => localStorage.getItem("talentcard-lang") || "fr",
  );
  const [wizardLoading, setWizardLoading] = useState(false);
  const [wizardError, setWizardError] = useState(null);
  const [uploadingCv, setUploadingCv]  = useState(false);
  const [uploadErrorCv, setUploadErrorCv] = useState("");

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

  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();

    const loadCvFiles = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}/cv-files`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => null);
        if (!res.ok || !data) return;

        setCvFiles(Array.isArray(data.cvFiles) ? data.cvFiles : []);
      } catch (e) {
        if (e.name === "AbortError") return;
      }
    };

    loadCvFiles();

    return () => controller.abort();
  }, [userId]);

  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();

    const loadTalentcardFiles = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}/talentcard-files`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => null);
        if (!res.ok || !data) return;

        setTalentcardFiles(Array.isArray(data.talentcardFiles) ? data.talentcardFiles : []);
      } catch (e) {
        if (e.name === "AbortError") return;
      }
    };

    loadTalentcardFiles();

    return () => controller.abort();
  }, [userId]);

  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();

    const loadApplications = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}/applications`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => null);
        if (!res.ok || !data) return;

        setApplications(Array.isArray(data.applications) ? data.applications : []);
      } catch (e) {
        if (e.name === "AbortError") return;
      }
    };

    loadApplications();

    return () => controller.abort();
  }, [userId]);

  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();

    const loadPortfolio = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}/portfolio`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => null);
        if (!res.ok || !data) return;

        setPortfolio(Array.isArray(data.projects) ? data.projects : []);
      } catch (e) {
        if (e.name === "AbortError") return;
      }
    };

    loadPortfolio();

    return () => controller.abort();
  }, [userId]);

  useEffect(() => {
    if (!userId) return;

    const controller = new AbortController();

    const loadPortfolioPdfs = async () => {
      try {
        const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}/portfolio-pdf-files`, {
          signal: controller.signal,
        });
        const data = await res.json().catch(() => null);
        if (!res.ok || !data) return;

        setPortfolioShort(Array.isArray(data.portfolioShort) ? data.portfolioShort : []);
        setPortfolioLong(Array.isArray(data.portfolioLong) ? data.portfolioLong : []);
      } catch (e) {
        if (e.name === "AbortError") return;
      }
    };

    loadPortfolioPdfs();

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

  const handleUploadCv = async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file || !userId) return;

    setUploadErrorCv("");

    if (!file.type.includes("pdf")) {
      setUploadErrorCv("Seuls les fichiers PDF sont acceptés.");
      event.target.value = "";
      return;
    }

    setUploadingCv(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE}/dashboard/candidat/${userId}/upload-cv`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json().catch(() => null);

      if (!res.ok || !data) {
        setUploadErrorCv(data?.message || "Erreur lors de l’upload du CV.");
        return;
      }

      setCvFiles((prev) => [data, ...prev]);
    } catch {
      setUploadErrorCv("Erreur de connexion au serveur.");
    } finally {
      setUploadingCv(false);
      event.target.value = "";
    }
  };

  // ── Logique simplifiée du wizard Talent Card (section Bienvenue) ──
  const wizardSteps = [
    {
      id: 1,
      title: "Comprendre ton profil",
      subtitle: "Qui tu es",
      aiMessage:
        " Salut ! Avant de commencer, je vais analyser ton profil pour comprendre ton contexte et adapter les opportunités qui te correspondent vraiment.",
      aiExplanation:
        "Ces informations m’aident à filtrer les opportunités qui matchent vraiment avec ta situation.",
      whatAiDoes:
        " Une fois ces informations remplies, je crée une carte d’identité professionnelle personnalisée.",
    },
    {
      id: 2,
      title: "Ton objectif professionnel",
      subtitle: "Ce que tu veux",
      aiMessage:
        " Je vais structurer tes aspirations pour créer une Talent Card qui met en avant ce que tu recherches.",
      aiExplanation:
        " Plus je comprends ce que tu veux, mieux je peux structurer ta candidature.",
      whatAiDoes:
        " Je transforme tes objectifs en un profil ciblé qui parle aux recruteurs.",
    },
    {
      id: 3,
      title: "Tes compétences",
      subtitle: "Ce que tu sais faire",
      aiMessage:
        " Je vais analyser ton CV ou ton LinkedIn pour extraire automatiquement tes compétences et expériences.",
      aiExplanation:
        " Au lieu de te faire remplir un long formulaire, je lis directement ton CV.",
      whatAiDoes:
        " J’utilise l’IA pour extraire et structurer tes expériences et réalisations.",
    },
    {
      id: 4,
      title: "Validation & génération",
      subtitle: "Ton profil est prêt",
      aiMessage:
        " Ton profil est complet, je peux générer une Talent Card PDF professionnelle.",
      aiExplanation:
        " Tu obtiendras une Talent Card PDF et un CV optimisé.",
      whatAiDoes:
        " Je génère la Talent Card, la sauvegarde et prépare ton CV optimisé.",
    },
  ];

  const isWizardStepComplete = (stepId) => {
    switch (stepId) {
      case 1:
        return (
          nationality &&
          locationCountry &&
          seniorityLevel &&
          disponibilite &&
          imgFile
        );
      case 2:
        return (
          targetPosition &&
          targetCountry &&
          constraints &&
          searchCriteria &&
          typeContrat.length > 0 &&
          domaineActivite
        );
      case 3:
        return cvFile || linkedinUrl.trim();
      case 4:
        return true;
      default:
        return false;
    }
  };

  const handleWizardFileChange = (e) => {
    const selectedFile = e.target.files && e.target.files[0];
    setCvFile(selectedFile || null);
  };

  const handleWizardRemoveCv = () => {
    setCvFile(null);
  };

  const handleWizardImageChange = (e) => {
    const selectedFile = e.target.files && e.target.files[0];
    setImgFile(selectedFile || null);
  };

  const handleWizardRemoveImage = () => {
    setImgFile(null);
  };

  const setTalentCardLangAndSave = (lang) => {
    setTalentCardLang(lang);
    localStorage.setItem("talentcard-lang", lang);
  };

  const currentStepData =
    wizardSteps.find((s) => s.id === currentWizardStep) || wizardSteps[0];

  const handleWizardNext = () => {
    if (currentWizardStep < 4 && isWizardStepComplete(currentWizardStep)) {
      setCurrentWizardStep((s) => s + 1);
    }
  };

  const handleWizardPrevious = () => {
    if (currentWizardStep > 1) {
      setCurrentWizardStep((s) => s - 1);
    }
  };

  const handleWizardSubmit = async (e) => {
    e.preventDefault();
    if (
      !isWizardStepComplete(1) ||
      !isWizardStepComplete(2) ||
      !isWizardStepComplete(3)
    ) {
      setWizardError(
        "Merci de compléter les étapes 1, 2 et 3 avant de générer la Talent Card.",
      );
      return;
    }
    setWizardLoading(true);
    setWizardError(null);
    try {
      // Ici tu pourras brancher ton appel API `${API_URL}/process`
      // pour l’instant on simule simplement la génération.
      // eslint-disable-next-line no-alert
      alert("Génération de la Talent Card (simulation côté front).");
    } finally {
      setWizardLoading(false);
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
                <p className="dash-page-sub">
                  Vos réalisations et projets · {portfolio.length} travaux et fichiers portfolio
                </p>
              </div>
              <div className="portfolio-shell">
                <div className="portfolio-tabs">
                  <button
                    type="button"
                    className={`portfolio-tab${pfTab==="grid"?" portfolio-tab--active":""}`}
                    onClick={()=>setPfTab("grid")}
                  >
                    Portfolio court
                  </button>
                  <button
                    type="button"
                    className={`portfolio-tab${pfTab==="list"?" portfolio-tab--active":""}`}
                    onClick={()=>setPfTab("list")}
                  >
                    Portfolio long
                  </button>
                </div>

                {pfTab === "grid" && (
                  <div className="pf-grid" key="grid">
                    {portfolioShort.length === 0 && portfolio.length === 0 ? (
                      <p>Aucun portfolio court (PDF ou projet) n’est encore disponible.</p>
                    ) : (
                      <>
                        {portfolioShort.length > 0 && (
                          <div className="pf-files-section">
                            <div className="files-list">
                              {portfolioShort.map((file) => {
                                const date = file.updatedAt
                                  ? new Date(file.updatedAt).toLocaleDateString("fr-FR", {
                                      year: "numeric",
                                      month: "short",
                                      day: "2-digit",
                                    })
                                  : "-";

                                return (
                                  <div className="files-row" key={file.path}>
                                    <div className="files-main">
                                      <div className="files-name">{file.name}</div>
                                      <div className="files-meta">
                                        <span>{date}</span>
                                      </div>
                                    </div>
                                    <div className="files-actions">
                                      <a
                                        href={file.publicUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="files-btn"
                                      >
                                        Ouvrir
                                      </a>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {portfolio.length > 0 && (
                          <div className="pf-grid" style={{ marginTop: 24 }}>
                            {portfolio.map((item, index) => {
                              const color = GRADIENTS[index % GRADIENTS.length];
                              const desc =
                                item.shortDescription ||
                                (item.longDescription
                                  ? `${item.longDescription.slice(0, 140)}…`
                                  : "");
                              const tags = Array.isArray(item.tags) ? item.tags : [];
                              return (
                                <div className="pf-card" key={item.id}>
                                  <div className="pf-thumb">
                                    <div className="pf-thumb-bg" style={{ background: color }} />
                                    <div className="pf-thumb-overlay" />
                                    <span className="pf-thumb-num">
                                      {String(index + 1).padStart(2, "0")}
                                    </span>
                                  </div>
                                  <div className="pf-body">
                                    <div className="pf-title">{item.title}</div>
                                    <div className="pf-desc">{desc}</div>
                                    <div className="pf-tags">
                                      {tags.map((t) => (
                                        <span className="pf-tag" key={t}>{t}</span>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

                {pfTab === "list" && (
                  <div className="pf-list" key="list">
                    {portfolioLong.length === 0 && portfolio.length === 0 ? (
                      <p>Aucun portfolio long (PDF ou projet) n’est encore disponible.</p>
                    ) : (
                      <>
                        {portfolioLong.length > 0 && (
                          <div className="pf-files-section">
                            <div className="files-list">
                              {portfolioLong.map((file) => {
                                const date = file.updatedAt
                                  ? new Date(file.updatedAt).toLocaleDateString("fr-FR", {
                                      year: "numeric",
                                      month: "short",
                                      day: "2-digit",
                                    })
                                  : "-";

                                return (
                                  <div className="files-row" key={file.path}>
                                    <div className="files-main">
                                      <div className="files-name">{file.name}</div>
                                      <div className="files-meta">
                                        <span>{date}</span>
                                      </div>
                                    </div>
                                    <div className="files-actions">
                                      <a
                                        href={file.publicUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="files-btn"
                                      >
                                        Ouvrir
                                      </a>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {portfolio.length > 0 && (
                          <div className="pf-list" style={{ marginTop: 24 }}>
                            {portfolio.map((item, index) => {
                              const color = GRADIENTS[index % GRADIENTS.length];
                              const tags = Array.isArray(item.tags) ? item.tags : [];
                              const date = item.createdAt
                                ? new Date(item.createdAt).toLocaleDateString("fr-FR", {
                                    year: "numeric",
                                    month: "short",
                                  })
                                : "";
                              const desc =
                                item.longDescription ||
                                item.shortDescription ||
                                "";

                              return (
                                <div className="pf-row" key={item.id}>
                                  <div className="pf-row-thumb">
                                    <div className="pf-row-thumb-bg" style={{ background: color }} />
                                  </div>
                                  <div className="pf-row-info">
                                    <div className="pf-row-title">{item.title}</div>
                                    <div className="pf-row-desc">{desc}</div>
                                    <div className="pf-tags" style={{ marginTop: 4 }}>
                                      {tags.map((t) => (
                                        <span className="pf-tag" key={t}>{t}</span>
                                      ))}
                                    </div>
                                  </div>
                                  <div className="pf-row-meta">
                                    <span className="pf-row-date">{date}</span>
                                    <ArrowRight size={15} className="pf-row-arrow" />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── BIENVENUE + MES FICHIERS (CV) ── */}
          {(active === "fichiers" || active === "cv") && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">
                  {active === "cv" ? "Mes CV" : "Bienvenue"}
                </h1>
                <p className="dash-page-sub">
                  {active === "cv"
                    ? "Gérez plusieurs versions de CV, activez celle de votre choix et consultez les statistiques en temps réel."
                    : <>Bienvenue dans votre espace TAP. Retrouvez ici tous vos CV enregistrés (fichiers commençant par <em>cv_</em>), et laissez l’IA vous aider à préparer votre Talent Card.</>}
                </p>
              </div>
              <div className="dash-section-page">
                {active === "fichiers" && (
                  <div className="dash-section-card" style={{ marginBottom: 24 }}>
                    {/* Header wizard */}
                    <div className="dash-page-header" style={{ marginBottom: 16 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "1rem",
                          marginBottom: "1rem",
                        }}
                      >
                        <img src={logo} alt="logo" style={{ width: "3rem" }} />
                        <h2
                          className="dash-page-title"
                          style={{ fontSize: 22, textTransform: "uppercase" }}
                        >
                          Talent Acceleration Platform
                        </h2>
                      </div>
                      <p className="dash-page-sub">
                        Je t&apos;accompagne pour créer ton profil professionnel étape par étape.
                      </p>
                    </div>

                    {/* Wizard progress */}
                    <div
                      className="welcome-wizard-steps"
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 8,
                        marginBottom: 16,
                        flexWrap: "wrap",
                      }}
                    >
                      {wizardSteps.map((step, index) => (
                        <React.Fragment key={step.id}>
                          <div
                            style={{
                              width: 36,
                              height: 36,
                              borderRadius: "999px",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: 13,
                              fontWeight: 600,
                              background:
                                currentWizardStep === step.id
                                  ? "#CA1B28"
                                  : currentWizardStep > step.id
                                  ? "#16a34a"
                                  : "#e5e7eb",
                              color:
                                currentWizardStep >= step.id ? "#fff" : "#374151",
                            }}
                          >
                            {currentWizardStep > step.id ? "✓" : step.id}
                          </div>
                          {index < wizardSteps.length - 1 && (
                            <div
                              style={{
                                width: 40,
                                height: 2,
                                background:
                                  currentWizardStep > step.id ? "#16a34a" : "#e5e7eb",
                              }}
                            />
                          )}
                        </React.Fragment>
                      ))}
                    </div>

                    {/* AI message */}
                    <div
                      style={{
                        marginBottom: 16,
                        borderLeft: "4px solid #CA1B28",
                        padding: 12,
                        background: "rgba(0,0,0,0.03)",
                        borderRadius: 8,
                      }}
                    >
                      <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                        <div
                          style={{
                            width: 40,
                            height: 40,
                            borderRadius: "999px",
                            background: "#fef2f2",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <img src={logo} alt="logo" style={{ width: "1.8rem" }} />
                        </div>
                        <div style={{ flex: 1 }}>
                          <h3
                            style={{
                              fontSize: 16,
                              fontWeight: 600,
                              marginBottom: 4,
                            }}
                          >
                            {currentStepData.title}
                          </h3>
                          <p style={{ marginBottom: 6 }}>{currentStepData.aiMessage}</p>
                          <div
                            style={{
                              background: "#fef2f2",
                              borderRadius: 8,
                              padding: 8,
                              border: "1px solid #fecaca",
                              fontSize: 13,
                            }}
                          >
                            <p style={{ marginBottom: 4 }}>
                              {currentStepData.aiExplanation}
                            </p>
                            <p>{currentStepData.whatAiDoes}</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Wizard form (simplifié) */}
                    {wizardError && (
                      <div
                        style={{
                          marginBottom: 12,
                          padding: 8,
                          borderRadius: 6,
                          background: "#fef2f2",
                          border: "1px solid #fecaca",
                          color: "#b91c1c",
                          fontSize: 14,
                        }}
                      >
                        {wizardError}
                      </div>
                    )}

                    <form
                      onSubmit={handleWizardSubmit}
                      className="contact-form"
                      style={{ background: "transparent", boxShadow: "none", border: "none" }}
                    >
                      {currentWizardStep === 1 && (
                        <>
                          <div className="form-row">
                            <div className="form-field">
                              <label>
                                Nationalité <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <input
                                type="text"
                                value={nationality}
                                onChange={(e) => setNationality(e.target.value)}
                                placeholder="Ex: Marocaine, Française, Canadienne..."
                                required
                              />
                            </div>
                            <div className="form-field">
                              <label>
                                Pays de résidence actuel{" "}
                                <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <input
                                type="text"
                                value={locationCountry}
                                onChange={(e) => setLocationCountry(e.target.value)}
                                placeholder="Ex: Maroc, France, Canada..."
                                required
                              />
                            </div>
                          </div>
                          <div className="form-row">
                            <div className="form-field">
                              <label>
                                Niveau de séniorité{" "}
                                <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <select
                                value={seniorityLevel}
                                onChange={(e) => setSeniorityLevel(e.target.value)}
                                required
                              >
                                <option value="">Sélectionner...</option>
                                <option value="Entry Level">
                                  Entry Level / Débutant
                                </option>
                                <option value="Junior">Junior</option>
                                <option value="Intermediate">Intermédiaire</option>
                                <option value="Mid-Level">
                                  Mid-Level / Confirmé
                                </option>
                                <option value="Senior">Senior</option>
                                <option value="Expert">Expert / Lead</option>
                              </select>
                            </div>
                            <div className="form-field">
                              <label>
                                Disponibilité{" "}
                                <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <select
                                value={disponibilite}
                                onChange={(e) => setDisponibilite(e.target.value)}
                                required
                              >
                                <option value="">Sélectionner...</option>
                                <option value="Immediat">Immédiate</option>
                                <option value="1 semaine">1 semaine</option>
                                <option value="2 semaines">2 semaines</option>
                                <option value="3 semaines">3 semaines</option>
                                <option value="4 semaines">4 semaines</option>
                                <option value="5 semaines">5 semaines</option>
                              </select>
                            </div>
                          </div>
                          <div className="form-field form-field-full">
                            <label>
                              Photo professionnelle{" "}
                              <span style={{ color: "#dc2626" }}>*</span>
                            </label>
                            <input
                              type="file"
                              accept=".jpg,.jpeg,.png"
                              onChange={handleWizardImageChange}
                            />
                            {imgFile && (
                              <div className="login-error" style={{ marginTop: 8 }}>
                                <span>✅</span>
                                <span style={{ marginLeft: 8 }}>{imgFile.name}</span>
                                <button
                                  type="button"
                                  onClick={handleWizardRemoveImage}
                                  style={{
                                    marginLeft: 12,
                                    color: "#dc2626",
                                    textDecoration: "underline",
                                    background: "none",
                                    border: "none",
                                    cursor: "pointer",
                                  }}
                                >
                                  Supprimer
                                </button>
                              </div>
                            )}
                          </div>
                        </>
                      )}

                      {currentWizardStep === 2 && (
                        <>
                          <div className="form-row">
                            <div className="form-field">
                              <label>
                                Poste cible{" "}
                                <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <input
                                type="text"
                                value={targetPosition}
                                onChange={(e) => setTargetPosition(e.target.value)}
                                placeholder="Ex: Data Scientist, Software Engineer..."
                                required
                              />
                            </div>
                            <div className="form-field">
                              <label>
                                Pays cible{" "}
                                <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <input
                                type="text"
                                value={targetCountry}
                                onChange={(e) => setTargetCountry(e.target.value)}
                                placeholder="Ex: France, Canada, USA..."
                                required
                              />
                            </div>
                          </div>
                          <div className="form-row">
                            <div className="form-field">
                              <label>Prêt à relocaliser</label>
                              <select
                                value={pretARelocater}
                                onChange={(e) => setPretARelocater(e.target.value)}
                              >
                                <option value="">Non spécifié</option>
                                <option value="Oui">Oui</option>
                                <option value="Non">Non</option>
                              </select>
                            </div>
                            <div className="form-field">
                              <label>
                                Salaire minimum{" "}
                                <span style={{ color: "#dc2626" }}>*</span>
                              </label>
                              <input
                                type="text"
                                value={salaireMinimum}
                                onChange={(e) => setSalaireMinimum(e.target.value)}
                                placeholder="Ex: 50000"
                                required
                              />
                            </div>
                          </div>
                          <div className="form-field form-field-full">
                            <label>
                              Exigences / Pré-requis{" "}
                              <span style={{ color: "#dc2626" }}>*</span>
                            </label>
                            <textarea
                              value={constraints}
                              onChange={(e) => setConstraints(e.target.value)}
                              rows={3}
                              required
                            />
                          </div>
                          <div className="form-field form-field-full">
                            <label>
                              Ce que tu recherches{" "}
                              <span style={{ color: "#dc2626" }}>*</span>
                            </label>
                            <textarea
                              value={searchCriteria}
                              onChange={(e) => setSearchCriteria(e.target.value)}
                              rows={3}
                              required
                            />
                          </div>
                          <div className="form-field form-field-full">
                            <label>
                              Types de contrat recherchés{" "}
                              <span style={{ color: "#dc2626" }}>*</span>
                            </label>
                            <div className="form-row">
                              {["CDI", "CDD", "Freelance", "Mission", "Stage"].map(
                                (type) => (
                                  <label
                                    key={type}
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: 4,
                                      cursor: "pointer",
                                      fontSize: 13,
                                    }}
                                  >
                                    <input
                                      type="checkbox"
                                      value={type}
                                      checked={typeContrat.includes(type)}
                                      onChange={(e) => {
                                        if (e.target.checked) {
                                          setTypeContrat((prev) => [...prev, type]);
                                        } else {
                                          setTypeContrat((prev) =>
                                            prev.filter((t) => t !== type),
                                          );
                                        }
                                      }}
                                    />
                                    <span>{type}</span>
                                  </label>
                                ),
                              )}
                            </div>
                          </div>
                          <div className="form-field form-field-full">
                            <label>
                              Domaine d&apos;activité{" "}
                              <span style={{ color: "#dc2626" }}>*</span>
                            </label>
                            <input
                              type="text"
                              value={domaineActivite}
                              onChange={(e) => setDomaineActivite(e.target.value)}
                              placeholder="Ex: Intelligence artificielle & Data"
                              required
                            />
                          </div>
                        </>
                      )}

                      {currentWizardStep === 3 && (
                        <>
                          <div className="form-row">
                            <div className="form-field">
                              <label>CV (PDF ou DOCX)</label>
                              <input
                                type="file"
                                accept=".pdf,.doc,.docx"
                                onChange={handleWizardFileChange}
                              />
                              {cvFile && (
                                <div className="login-error" style={{ marginTop: 8 }}>
                                  <span>✅</span>
                                  <span style={{ marginLeft: 8 }}>{cvFile.name}</span>
                                  <button
                                    type="button"
                                    onClick={handleWizardRemoveCv}
                                    style={{
                                      marginLeft: 12,
                                      color: "#dc2626",
                                      textDecoration: "underline",
                                      background: "none",
                                      border: "none",
                                      cursor: "pointer",
                                    }}
                                  >
                                    Supprimer
                                  </button>
                                </div>
                              )}
                            </div>
                            <div className="form-field">
                              <label>OU URL LinkedIn</label>
                              <input
                                type="url"
                                value={linkedinUrl}
                                onChange={(e) => setLinkedinUrl(e.target.value)}
                                placeholder="https://www.linkedin.com/in/..."
                              />
                            </div>
                          </div>
                          <div className="form-field form-field-full">
                            <label>URL GitHub</label>
                            <input
                              type="url"
                              value={githubUrl}
                              onChange={(e) => setGithubUrl(e.target.value)}
                              placeholder="https://github.com/..."
                            />
                          </div>
                        </>
                      )}

                      {currentWizardStep === 4 && (
                        <div style={{ textAlign: "center" }}>
                          <p style={{ marginBottom: 8 }}>
                            ✅ Ton profil est complet !
                          </p>
                          <p style={{ marginBottom: 8, fontSize: 14 }}>
                            Choisis la langue de ta Talent Card :
                          </p>
                          <div
                            style={{
                              display: "inline-flex",
                              background: "rgba(0,0,0,0.06)",
                              borderRadius: 999,
                              padding: 4,
                              marginBottom: 12,
                            }}
                          >
                            <button
                              type="button"
                              onClick={() => setTalentCardLangAndSave("fr")}
                              style={{
                                padding: "6px 14px",
                                borderRadius: 999,
                                border: "none",
                                cursor: "pointer",
                                background:
                                  talentCardLang === "fr" ? "#C1121F" : "transparent",
                                color:
                                  talentCardLang === "fr" ? "#fff" : "inherit",
                              }}
                            >
                              FR
                            </button>
                            <button
                              type="button"
                              onClick={() => setTalentCardLangAndSave("en")}
                              style={{
                                padding: "6px 14px",
                                borderRadius: 999,
                                border: "none",
                                cursor: "pointer",
                                background:
                                  talentCardLang === "en" ? "#C1121F" : "transparent",
                                color:
                                  talentCardLang === "en" ? "#fff" : "inherit",
                              }}
                            >
                              EN
                            </button>
                          </div>
                          <p style={{ fontSize: 14 }}>
                            En cliquant sur &quot;Générer ma Talent Card&quot;, nous
                            lancerons le traitement IA (à connecter à l&apos;API).
                          </p>
                        </div>
                      )}

                      {/* Navigation */}
                      <div className="contact-submit-wrapper" style={{ marginTop: 16 }}>
                        {currentWizardStep > 1 ? (
                          <button
                            type="button"
                            onClick={handleWizardPrevious}
                            className="contact-submit"
                          >
                            ← Précédent
                          </button>
                        ) : (
                          <span />
                        )}
                        {currentWizardStep < 4 ? (
                          <button
                            type="button"
                            onClick={handleWizardNext}
                            className="contact-submit"
                            disabled={!isWizardStepComplete(currentWizardStep)}
                          >
                            Suivant →
                          </button>
                        ) : (
                          <button
                            type="submit"
                            className="contact-submit"
                            disabled={
                              wizardLoading ||
                              !isWizardStepComplete(1) ||
                              !isWizardStepComplete(2) ||
                              !isWizardStepComplete(3)
                            }
                          >
                            {wizardLoading
                              ? "Génération en cours..."
                              : "🚀 Générer ma Talent Card"}
                          </button>
                        )}
                      </div>
                    </form>
                  </div>
                )}
                {active === "cv" && (
                <div className="dash-section-card">
                  <div className="files-upload-bar">
                    <label className="files-upload-btn">
                      {uploadingCv ? "Import du CV en cours…" : "Importer un nouveau CV"}
                      <input
                        type="file"
                        accept="application/pdf"
                        onChange={handleUploadCv}
                        disabled={uploadingCv}
                      />
                    </label>
                    <p className="files-upload-hint">
                      Formats acceptés : PDF. Le fichier sera stocké dans votre dossier sécurisé TAP.
                    </p>
                  </div>

                  {uploadErrorCv && (
                    <div className="login-error" style={{ marginTop: 12 }}>
                      <span>⚠</span> {uploadErrorCv}
                    </div>
                  )}

                  {cvFiles.length === 0 ? (
                    <p>Aucun CV enregistré pour l’instant.</p>
                  ) : (
                    <div className="files-list">
                      {cvFiles.map((file) => {
                        const date = file.updatedAt
                          ? new Date(file.updatedAt).toLocaleDateString("fr-FR", {
                              year: "numeric",
                              month: "short",
                              day: "2-digit",
                            })
                          : "-";

                        const sizeKb =
                          typeof file.size === "number"
                            ? Math.round(file.size / 1024)
                            : null;

                        return (
                          <div className="files-row" key={file.path}>
                            <div className="files-main">
                              <div className="files-name">{file.name}</div>
                              <div className="files-meta">
                                <span>{date}</span>
                                {sizeKb !== null && (
                                  <span>· {sizeKb} Ko</span>
                                )}
                              </div>
                            </div>
                            <div className="files-actions">
                              <a
                                href={file.publicUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="files-btn"
                              >
                                Télécharger
                              </a>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
                )}
              </div>
            </div>
          )}

          {/* ── TALENT CARD ── */}
          {active === "talentcard" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Talent Card</h1>
                <p className="dash-page-sub">
                  Consultez vos Talent Cards générées (PDF commençant par <em>talentcard</em>).
                </p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  {talentcardFiles.length === 0 ? (
                    <p>Aucune Talent Card PDF enregistrée pour le moment.</p>
                  ) : (
                    <div className="files-list">
                      {talentcardFiles.map((file) => {
                        const date = file.updatedAt
                          ? new Date(file.updatedAt).toLocaleDateString("fr-FR", {
                              year: "numeric",
                              month: "short",
                              day: "2-digit",
                            })
                          : "-";

                        const sizeKb =
                          typeof file.size === "number"
                            ? Math.round(file.size / 1024)
                            : null;

                        return (
                          <div className="files-row" key={file.path}>
                            <div className="files-main">
                              <div className="files-name">{file.name}</div>
                              <div className="files-meta">
                                <span>{date}</span>
                                {sizeKb !== null && (
                                  <span>· {sizeKb} Ko</span>
                                )}
                              </div>
                            </div>
                            <div className="files-actions">
                              <a
                                href={file.publicUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="files-btn"
                              >
                                Ouvrir
                              </a>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── MES CANDIDATURES ── */}
          {active === "candidatures" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Mes candidatures</h1>
                <p className="dash-page-sub">
                  Suivez le statut de chacune de vos candidatures et les postes associés.
                </p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  {applications.length === 0 ? (
                    <p>Aucune candidature enregistrée pour le moment.</p>
                  ) : (
                    <div className="cand-list">
                      {applications.map((app) => {
                        const status = (app.status || "").toUpperCase();
                        let statusLabel = "En cours";
                        let statusClass = "cand-status-pill--pending";
                        if (status === "ACCEPTEE") {
                          statusLabel = "Acceptée";
                          statusClass = "cand-status-pill--accepted";
                        } else if (status === "REFUSEE") {
                          statusLabel = "Refusée";
                          statusClass = "cand-status-pill--refused";
                        }

                        const date = app.validatedAt
                          ? new Date(app.validatedAt).toLocaleDateString("fr-FR", {
                              year: "numeric",
                              month: "short",
                              day: "2-digit",
                            })
                          : "-";

                        return (
                          <div className="cand-row" key={app.id}>
                            <div className="cand-job">
                              <div className="cand-job-title">
                                {app.jobTitle || "Poste non renseigné"}
                              </div>
                              {app.company && (
                                <div className="cand-job-company">
                                  {app.company}
                                </div>
                              )}
                            </div>
                            <div className="cand-status">
                              <span className={`cand-status-pill ${statusClass}`}>
                                {statusLabel}
                              </span>
                            </div>
                            <div className="cand-date">
                              <span>{date}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── OTHER PAGES ── */}
          {active !== "dashboard" &&
           active !== "portfolio" &&
           active !== "candidatures" &&
           active !== "fichiers" &&
           active !== "cv" &&
           active !== "talentcard" && (
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
