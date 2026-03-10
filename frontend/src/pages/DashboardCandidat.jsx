import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, FolderOpen, CreditCard, FileText,
  Image, CalendarCheck, LogOut, Search,
  TrendingUp, TrendingDown, Users, Bookmark, Bell,
  BriefcaseBusiness, ArrowRight, ChevronLeft, ChevronRight,
  Settings, Menu, Award, Zap, BarChart2, AlertTriangle,
} from "lucide-react";
import "../css/Dashboard.css";
import logo from "../assets/logo-white.svg";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

/* ─── gradients portfolio ─── */
const GRADIENTS = [
  "linear-gradient(145deg,#2a0a0a 0%,#4a1010 100%)",
  "linear-gradient(145deg,#0a0a1a 0%,#1a1a3a 100%)",
  "linear-gradient(145deg,#0a1a0a 0%,#1a3a1a 100%)",
  "linear-gradient(145deg,#1a0a1a 0%,#3a1a3a 100%)",
  "linear-gradient(145deg,#1a1a0a 0%,#3a3a1a 100%)",
  "linear-gradient(145deg,#0a1a1a 0%,#1a3a3a 100%)",
];

/* ─── menu ─── */
const MENU = [
  { id: "dashboard",    label: "Dashboard",         icon: LayoutDashboard   },
  { id: "fichiers",     label: "Bienvenue",          icon: FolderOpen        },
  { id: "talentcard",   label: "Talent Card",        icon: CreditCard        },
  { id: "cv",           label: "Curriculum Vitae",   icon: FileText          },
  { id: "portfolio",    label: "Portfolio Court",    icon: Image             },
  { id: "portfolio-long","label": "Portfolio Long",  icon: BarChart2         },
  { id: "candidatures", label: "Mes candidatures",   icon: BriefcaseBusiness },
  { id: "entretiens",   label: "Entretiens",         icon: CalendarCheck     },
];

/* ─── bar chart data ─── */
const BAR_DATA = [
  { label:"Jan",v:52 },{ label:"Fév",v:68 },{ label:"Mar",v:41 },
  { label:"Avr",v:85 },{ label:"Mai",v:63 },{ label:"Jun",v:77 },
  { label:"Jul",v:48 },{ label:"Aoû",v:72 },{ label:"Sep",v:91 },
];

/* ─── helpers ─── */
function useCountUp(target, duration = 1100) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (target === null || target === undefined) return;
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setVal(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return val;
}

function StatCard({ label, value, icon: Icon, trend, dir, danger, delay }) {
  const count = useCountUp(value ?? 0, 1100);
  const [vis, setVis] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVis(true), delay ?? 0); return () => clearTimeout(t); }, [delay]);
  return (
    <div className={`dash-card${danger ? " dash-card--danger" : ""}`}
      style={{ opacity: vis?1:0, transform: vis?"translateY(0)":"translateY(28px)", transition:"opacity .55s ease,transform .55s ease" }}>
      <div className="dash-card-row1">
        <span className="dash-card-label">{label}</span>
        <div className="dash-card-icon-wrap"><Icon size={14} /></div>
      </div>
      <div className="dash-card-value">{value === null ? "—" : count}</div>
      <div className={`dash-card-trend dash-card-trend--${dir==="up"?"up":dir==="down"?"down":"flat"}`}>
        {dir==="up"   && <TrendingUp size={11} />}
        {dir==="down" && <TrendingDown size={11} />}
        {trend}
      </div>
    </div>
  );
}

function BarChart() {
  const [animated, setAnimated] = useState(false);
  const [hovered,  setHovered]  = useState(null);
  useEffect(() => { const t = setTimeout(() => setAnimated(true), 600); return () => clearTimeout(t); }, []);
  return (
    <div className="dash-chart">
      {BAR_DATA.map((d, i) => (
        <div key={d.label} className="dash-chart-bar-wrap">
          <div className="dash-bar"
            style={{ height: animated ? `${d.v}%`:"0%", transitionDelay:`${i*0.06}s`, position:"relative" }}
            onMouseEnter={() => setHovered(i)} onMouseLeave={() => setHovered(null)}>
            {hovered === i && <div className="dash-bar-tooltip">{d.v}</div>}
          </div>
          <span className="dash-bar-label">{d.label}</span>
        </div>
      ))}
    </div>
  );
}

function ProgressBar({ label, pct, colorClass, delay }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(pct), (delay??0)+500); return () => clearTimeout(t); }, [pct, delay]);
  return (
    <div className="dash-status-item">
      <div className="dash-status-row">
        <span className="dash-status-name">{label}</span>
        <span className="dash-status-pct">{pct}%</span>
      </div>
      <div className="dash-status-track">
        <div className={`dash-status-bar dash-status-bar--${colorClass}`} style={{ width:`${w}%` }} />
      </div>
    </div>
  );
}

function DimBar({ label, val, delay }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(val), (delay??0)+600); return () => clearTimeout(t); }, [val, delay]);
  return (
    <div className="dash-dim-item">
      <div className="dash-dim-row">
        <span className="dash-dim-name">{label}</span>
        <span className="dash-dim-val">{val?.toFixed ? val.toFixed(1) : val}</span>
      </div>
      <div className="dash-dim-track">
        <div className="dash-dim-bar" style={{ width:`${Math.min((w/10)*100,100)}%` }} />
      </div>
    </div>
  );
}

/* ════════════════════════════════════════
   MAIN COMPONENT
════════════════════════════════════════ */
export default function DashboardCandidat() {
  const navigate = useNavigate();

  const [active,             setActive]             = useState("dashboard");
  const [pfTab,              setPfTab]              = useState("grid");
  const [collapsed,          setCollapsed]          = useState(false);
  const [mobileSidebarOpen,  setMobileSidebarOpen]  = useState(false);
  const [showNotif,          setShowNotif]          = useState(false);
  const [showProfile,        setShowProfile]        = useState(false);

  /* ── API state ── */
  const [stats, setStats] = useState({
    applications: null, interviews: null,
    savedOffers: null,  notifications: null,
    statusPending: null, statusAccepted: null, statusRefused: null,
  });
  const [scoreData,      setScoreData]      = useState(null);   // from /score endpoint
  const [llmData,        setLlmData]        = useState(null);   // from /llm-evaluation endpoint
  const [skillsList,     setSkillsList]     = useState([]);     // from /skills endpoint
  const [portfolio,      setPortfolio]      = useState([]);
  const [portfolioShort, setPortfolioShort] = useState([]);
  const [portfolioLong,  setPortfolioLong]  = useState([]);
  const [applications,   setApplications]   = useState([]);
  const [cvFiles,        setCvFiles]        = useState([]);
  const [talentcardFiles,setTalentcardFiles]= useState([]);
  const [uploadingCv,    setUploadingCv]    = useState(false);
  const [uploadErrorCv,  setUploadErrorCv]  = useState("");

  /* ── wizard ── */
  const [currentWizardStep, setCurrentWizardStep] = useState(1);
  const [cvFile,          setCvFile]          = useState(null);
  const [imgFile,         setImgFile]         = useState(null);
  const [linkedinUrl,     setLinkedinUrl]     = useState("");
  const [githubUrl,       setGithubUrl]       = useState("");
  const [targetPosition,  setTargetPosition]  = useState("");
  const [targetCountry,   setTargetCountry]   = useState("");
  const [pretARelocater,  setPretARelocater]  = useState("");
  const [constraints,     setConstraints]     = useState("");
  const [searchCriteria,  setSearchCriteria]  = useState("");
  const [nationality,     setNationality]     = useState("");
  const [locationCountry, setLocationCountry] = useState("");
  const [seniorityLevel,  setSeniorityLevel]  = useState("");
  const [disponibilite,   setDisponibilite]   = useState("");
  const [typeContrat,     setTypeContrat]     = useState([]);
  const [salaireMinimum,  setSalaireMinimum]  = useState("");
  const [domaineActivite, setDomaineActivite] = useState("");
  const [talentCardLang,  setTalentCardLang]  = useState(() => localStorage.getItem("talentcard-lang") || "fr");
  const [wizardLoading,   setWizardLoading]   = useState(false);
  const [wizardError,     setWizardError]     = useState(null);

  const notifRef   = useRef(null);
  const profileRef = useRef(null);

  const userEmail = sessionStorage.getItem("userEmail") || "vous@exemple.com";
  const rawName   = sessionStorage.getItem("userName")  || userEmail.split("@")[0];
  const userName  = rawName.charAt(0).toUpperCase() + rawName.slice(1);
  const userId    = sessionStorage.getItem("userId");

  /* ── close dropdowns ── */
  useEffect(() => {
    const fn = (e) => {
      if (notifRef.current   && !notifRef.current.contains(e.target))   setShowNotif(false);
      if (profileRef.current && !profileRef.current.contains(e.target)) setShowProfile(false);
    };
    document.addEventListener("mousedown", fn);
    return () => document.removeEventListener("mousedown", fn);
  }, []);

  /* ── fetch stats ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}`, { signal: c.signal })
      .then(r => r.json()).then(data => {
        if (!data) return;
        setStats({
          applications:  data.applications  ?? 0,
          interviews:    data.interviews    ?? 0,
          savedOffers:   data.savedOffers   ?? 0,
          notifications: data.notifications ?? 0,
          statusPending:  data.statusPending  ?? 0,
          statusAccepted: data.statusAccepted ?? 0,
          statusRefused:  data.statusRefused  ?? 0,
        });
      }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch score (table: score + llm_evaluation_v2) ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/score`, { signal: c.signal })
      .then(r => r.json()).then(data => { if (data) setScoreData(data); }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch LLM evaluation ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/llm-evaluation`, { signal: c.signal })
      .then(r => r.json()).then(data => { if (data) setLlmData(data); }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch skills (table: skills) ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/skills`, { signal: c.signal })
      .then(r => r.json()).then(data => {
        if (data && Array.isArray(data.skills)) setSkillsList(data.skills);
      }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch cv-files ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/cv-files`, { signal: c.signal })
      .then(r => r.json()).then(data => { if (data) setCvFiles(Array.isArray(data.cvFiles) ? data.cvFiles : []); }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch talentcard-files ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/talentcard-files`, { signal: c.signal })
      .then(r => r.json()).then(data => { if (data) setTalentcardFiles(Array.isArray(data.talentcardFiles) ? data.talentcardFiles : []); }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch applications ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/applications`, { signal: c.signal })
      .then(r => r.json()).then(data => { if (data) setApplications(Array.isArray(data.applications) ? data.applications : []); }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch portfolio ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/portfolio`, { signal: c.signal })
      .then(r => r.json()).then(data => { if (data) setPortfolio(Array.isArray(data.projects) ? data.projects : []); }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── fetch portfolio PDFs ── */
  useEffect(() => {
    if (!userId) return;
    const c = new AbortController();
    fetch(`${API_BASE}/dashboard/candidat/${userId}/portfolio-pdf-files`, { signal: c.signal })
      .then(r => r.json()).then(data => {
        if (data) {
          setPortfolioShort(Array.isArray(data.portfolioShort) ? data.portfolioShort : []);
          setPortfolioLong(Array.isArray(data.portfolioLong)   ? data.portfolioLong  : []);
        }
      }).catch(() => {});
    return () => c.abort();
  }, [userId]);

  /* ── derived ── */
  const currentLabel = MENU.find(m => m.id === active)?.label ?? "Dashboard";
  const unreadCount  = stats.notifications ?? 0;

  const totalStatus = (stats.statusPending??0) + (stats.statusAccepted??0) + (stats.statusRefused??0);
  const pct = (n) => totalStatus ? Math.round(((n??0)/totalStatus)*100) : 0;

  const statusChart = [
    { key:"pending",  label:"En cours",  colorClass:"cr",    count:stats.statusPending??0,  p:pct(stats.statusPending)  },
    { key:"accepted", label:"Acceptées", colorClass:"green", count:stats.statusAccepted??0, p:pct(stats.statusAccepted) },
    { key:"refused",  label:"Refusées",  colorClass:"mute",  count:stats.statusRefused??0,  p:pct(stats.statusRefused)  },
  ];

  const statCards = [
    { label:"Candidatures",        value:stats.applications,  icon:BriefcaseBusiness, trend:"+3 ce mois",       dir:"up",   delay:60  },
    { label:"Entretiens",          value:stats.interviews,    icon:CalendarCheck,     trend:"+1 cette semaine", dir:"up",   delay:120 },
    { label:"Offres sauvegardées", value:stats.savedOffers,   icon:Bookmark,          trend:"Inchangé",         dir:"flat", delay:180 },
    { label:"Notifications",       value:stats.notifications, icon:Bell,              trend:"Non lues",         dir:"flat", delay:240, danger:true },
  ];

  /* score dimensions (from table: score) */
  const scoreDims = scoreData ? [
    { label:"Impact",       val: scoreData.dim_impact            ?? 0 },
    { label:"Hard Skills",  val: scoreData.dim_hard_skills_depth ?? 0 },
    { label:"Cohérence",    val: scoreData.dim_coherence         ?? 0 },
    { label:"Rareté",       val: scoreData.dim_rarete_marche     ?? 0 },
    { label:"Stabilité",    val: scoreData.dim_stabilite         ?? 0 },
    { label:"Communication",val: scoreData.dim_communication     ?? 0 },
  ] : [];

  /* anomalies from llm_evaluation_v2 */
  const anomalies = llmData ? [
    { key:"Surdéclaration séniorité",     val: llmData.anomalie_surdeclaration_seniority },
    { key:"Compétences sans preuves",     val: llmData.anomalie_competences_sans_preuves },
    { key:"Absence métriques chiffrées",  val: llmData.anomalie_absence_metriques_chiffrees },
    { key:"Incohérence majeure parcours", val: llmData.anomalie_incoherence_majeure_parcours },
    { key:"Keyword stuffing probable",    val: llmData.anomalie_keyword_stuffing_probable },
  ] : [];

  const decisionClass = scoreData?.decision
    ? `dash-score-ring-decision--${scoreData.decision.toLowerCase()}`
    : "";

  /* ── handlers ── */
  const logout = () => {
    ["authToken","profileType","userEmail","userId","userName"].forEach(k => sessionStorage.removeItem(k));
    navigate("/connexion");
  };

  const handleUploadCv = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !userId) return;
    setUploadErrorCv("");
    if (!file.type.includes("pdf")) { setUploadErrorCv("Seuls les fichiers PDF sont acceptés."); event.target.value=""; return; }
    setUploadingCv(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res  = await fetch(`${API_BASE}/dashboard/candidat/${userId}/upload-cv`, { method:"POST", body:fd });
      const data = await res.json().catch(()=>null);
      if (!res.ok || !data) { setUploadErrorCv(data?.message||"Erreur upload."); return; }
      setCvFiles(p => [data,...p]);
    } catch { setUploadErrorCv("Erreur de connexion."); }
    finally  { setUploadingCv(false); event.target.value=""; }
  };

  /* ── wizard ── */
  const wizardSteps = [
    { id:1, title:"Comprendre ton profil",      aiMessage:"Je vais analyser ton profil pour comprendre ton contexte.",            aiExplanation:"Ces infos m'aident à filtrer les opportunités.",  whatAiDoes:"Je crée ta carte d'identité professionnelle." },
    { id:2, title:"Ton objectif professionnel", aiMessage:"Je vais structurer tes aspirations pour créer une Talent Card ciblée.", aiExplanation:"Mieux je comprends tes attentes, meilleure est ta candidature.", whatAiDoes:"Je transforme tes objectifs en profil recruteur." },
    { id:3, title:"Tes compétences",             aiMessage:"Je vais analyser ton CV ou LinkedIn pour extraire tes compétences.",    aiExplanation:"Je lis directement ton CV plutôt qu'un long formulaire.",      whatAiDoes:"J'extrais et structure tes expériences par IA." },
    { id:4, title:"Validation & génération",    aiMessage:"Ton profil est complet — génération de ta Talent Card.",               aiExplanation:"Tu obtiendras une Talent Card PDF et un CV optimisé.", whatAiDoes:"Je génère et sauvegarde ta Talent Card." },
  ];
  const isStepComplete = (s) => {
    if (s===1) return !!(nationality && locationCountry && seniorityLevel && disponibilite && imgFile);
    if (s===2) return !!(targetPosition && targetCountry && constraints && searchCriteria && typeContrat.length && domaineActivite);
    if (s===3) return !!(cvFile || linkedinUrl.trim());
    return true;
  };
  const currentStepData = wizardSteps.find(s => s.id === currentWizardStep) || wizardSteps[0];

  const handleWizardSubmit = async (e) => {
    e.preventDefault();
    if (!isStepComplete(1)||!isStepComplete(2)||!isStepComplete(3)) { setWizardError("Complétez les étapes 1, 2 et 3."); return; }
    setWizardLoading(true); setWizardError(null);
    try { alert("Génération de la Talent Card (simulation)."); }
    finally { setWizardLoading(false); }
  };
  const setTalentCardLangAndSave = (lang) => { setTalentCardLang(lang); localStorage.setItem("talentcard-lang", lang); };

  /* ── render files helper ── */
  const renderFiles = (files, emptyMsg) => files.length === 0
    ? <p>{emptyMsg}</p>
    : <div className="files-list">
        {files.map(file => {
          const date   = file.updatedAt ? new Date(file.updatedAt).toLocaleDateString("fr-FR",{year:"numeric",month:"short",day:"2-digit"}) : "-";
          const sizeKb = typeof file.size==="number" ? Math.round(file.size/1024) : null;
          return (
            <div className="files-row" key={file.path}>
              <div className="files-main">
                <div className="files-name">{file.name}</div>
                <div className="files-meta"><span>{date}</span>{sizeKb!==null&&<span>· {sizeKb} Ko</span>}</div>
              </div>
              <div className="files-actions">
                <a href={file.publicUrl} target="_blank" rel="noopener noreferrer" className="files-btn">Ouvrir</a>
              </div>
            </div>
          );
        })}
      </div>;

  /* ════════════════════════════════════════
     RENDER
  ════════════════════════════════════════ */
  return (
    <section className="dash-section">
      <div className={`dash-layout${collapsed?" dash-layout--collapsed":""}`}>

        {/* ══════ SIDEBAR ══════ */}
        <aside className={`dash-sidebar${mobileSidebarOpen?" dash-sidebar--open":""}`}>

          {/* logo */}
          <div className="dash-logo-zone">
            <img src={logo} alt="TAP" className="dash-logo-img" />
            
          </div>

          {/* nav */}
          <nav className="dash-nav">
            <div className="dash-nav-section-label">Navigation</div>
            {MENU.map(({ id, label, icon: Icon }) => (
              <button key={id} type="button" data-label={label}
                className={`dash-menu-item${active===id?" dash-menu-item--active":""}`}
                onClick={() => { setActive(id); setMobileSidebarOpen(false); }}>
                <span className="dash-menu-icon"><Icon size={16} strokeWidth={active===id?2:1.5} /></span>
                <span className="dash-menu-label">{label}</span>
              </button>
            ))}
          </nav>

          {/* footer */}
          <div className="dash-sidebar-footer">
            <button type="button" className="dash-logout" onClick={logout}>
              <LogOut size={15} strokeWidth={1.5} />
              <span className="dash-logout-label">Se déconnecter</span>
            </button>
          </div>

          {/* collapse */}
          <div className="dash-collapse-btn" role="button" tabIndex={0}
            onClick={() => setCollapsed(v => !v)}
            onKeyDown={e => e.key==="Enter" && setCollapsed(v => !v)}>
            {collapsed ? <ChevronRight size={13} strokeWidth={2.5}/> : <ChevronLeft size={13} strokeWidth={2.5}/>}
          </div>
        </aside>

        {/* mobile overlay */}
        {mobileSidebarOpen && (
          <div onClick={() => setMobileSidebarOpen(false)}
            style={{ position:"fixed",inset:0,background:"rgba(0,0,0,0.75)",zIndex:99 }} />
        )}

        {/* ══════ MAIN ══════ */}
        <main className="dash-main">

          {/* topbar */}
          <div className="dash-topbar">
            <div className="dash-topbar-left">
              <button className="dash-topbar-toggle" type="button" onClick={() => setMobileSidebarOpen(v=>!v)}>
                <Menu size={15}/>
              </button>
              {/* logo in topbar */}
              
              <div className="dash-breadcrumb">
                <span style={{color:"var(--t3)"}}>Espace</span>
                <span className="dash-breadcrumb-sep">›</span>
                <span className="dash-breadcrumb-current">{currentLabel}</span>
              </div>
            </div>
            <div className="dash-topbar-right">
              <div className="dash-search-wrap">
                <Search size={13} color="var(--t3)"/>
                <input type="search" className="dash-search" placeholder="Rechercher…"/>
              </div>

              {/* bell */}
              <div className="dash-notif-wrap" ref={notifRef}>
                <div className="dash-notif-trigger" role="button" tabIndex={0}
                  onClick={() => { setShowNotif(v=>!v); setShowProfile(false); }}
                  onKeyDown={e => e.key==="Enter"&&setShowNotif(v=>!v)}>
                  <Bell size={16} strokeWidth={1.5}/>
                  {unreadCount>0 && <span className="dash-notif-badge">{unreadCount}</span>}
                </div>
                {showNotif && (
                  <div className="dash-notif-dropdown">
                    <div className="dash-notif-header">
                      <span>Notifications</span>
                      <span className="dash-notif-count">{unreadCount} non lues</span>
                    </div>
                    <div className="dash-notif-item dash-notif-item--unread">
                      <div className="dash-notif-dot"/>
                      <div className="dash-notif-body">
                        <p className="dash-notif-text">Vous avez {unreadCount} notification(s) liée(s) à votre activité récente.</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* avatar */}
              <div className="dash-profile-wrap" ref={profileRef}>
                <div className={`dash-topbar-avatar${showProfile?" dash-topbar-avatar--active":""}`}
                  role="button" tabIndex={0} aria-label="Profil"
                  onClick={() => { setShowProfile(v=>!v); setShowNotif(false); }}
                  onKeyDown={e => e.key==="Enter"&&setShowProfile(v=>!v)}>
                  {userName.charAt(0).toUpperCase()}
                </div>
                {showProfile && (
                  <div className="dash-profile-dropdown">
                    <div className="dash-profile-header">
                      <div className="dash-profile-avatar-lg">{userName.charAt(0).toUpperCase()}</div>
                      <div className="dash-profile-info">
                        <span className="dash-profile-name">{userName}</span>
                        <span className="dash-profile-email">{userEmail}</span>
                      </div>
                    </div>
                    <div className="dash-profile-divider"/>
                    <button className="dash-profile-action" type="button"><Settings size={13} strokeWidth={1.5}/> Paramètres</button>
                    <button className="dash-profile-action dash-profile-action--logout" type="button" onClick={logout}><LogOut size={13} strokeWidth={1.5}/> Se déconnecter</button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ═══════════════════════════════════
              DASHBOARD
          ═══════════════════════════════════ */}
          {active === "dashboard" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Bonjour, <em>{userName}</em></h1>
                <p className="dash-page-sub">
                  Aperçu complet de votre profil TAP · {new Date().toLocaleDateString("fr-FR",{weekday:"long",day:"numeric",month:"long"})}
                </p>
              </div>

              {/* stat cards */}
              <div className="dash-cards-row">
                {statCards.map(card => <StatCard key={card.label} {...card}/>)}
              </div>

              {/* row 1 : bar chart + candidature status */}
              <div className="dash-grid-2">
                <div className="dash-panel dash-panel-1">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Activité mensuelle</span>
                    <span className="dash-panel-chip">Live</span>
                  </div>
                  <BarChart/>
                </div>
                <div className="dash-panel dash-panel-2">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Candidatures par statut</span>
                    <Users size={14} color="var(--t3)"/>
                  </div>
                  <div className="dash-status-list">
                    {statusChart.map(({key,label,colorClass,count,p}) => (
                      <ProgressBar key={key} label={`${label} · ${count}`} pct={p} colorClass={colorClass} delay={80}/>
                    ))}
                  </div>
                </div>
              </div>

              {/* row 2 : score global + score dims */}
              <div className="dash-grid-21">
                {/* score ring */}
                <div className="dash-panel dash-panel-3">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Score TAP · Dimensions</span>
                    <Award size={14} color="var(--cr)"/>
                  </div>
                  {scoreData ? (
                    <div style={{ display:"flex", gap:24, alignItems:"flex-start" }}>
                      <div className="dash-score-ring">
                        <svg width={110} height={110} viewBox="0 0 36 36" style={{transform:"rotate(-90deg)"}}>
                          <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="3.2"/>
                          <circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--cr)" strokeWidth="3.2"
                            strokeDasharray={`${(scoreData.score_global/10)*100} 100`}
                            strokeLinecap="round"
                            style={{transition:"stroke-dasharray 1.6s cubic-bezier(0.22,1,0.36,1)"}}/>
                        </svg>
                        <div className="dash-score-ring-val">
                          {scoreData.score_global?.toFixed(1)}<span>/10</span>
                        </div>
                        <div className="dash-score-ring-label">Score Global</div>
                        {scoreData.decision && (
                          <span className={`dash-score-ring-decision ${decisionClass}`}>{scoreData.decision}</span>
                        )}
                      </div>
                      <div className="dash-dim-list" style={{flex:1}}>
                        {scoreDims.map((d,i) => <DimBar key={d.label} label={d.label} val={d.val} delay={i*80}/>)}
                      </div>
                    </div>
                  ) : (
                    <p style={{color:"var(--t3)",fontSize:13}}>Aucun score disponible — générez votre Talent Card.</p>
                  )}
                </div>

                {/* LLM badges */}
                <div className="dash-panel dash-panel-4">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Profil IA</span>
                    <Zap size={14} color="var(--cr)"/>
                  </div>
                  {llmData ? (
                    <div className="dash-llm-grid">
                      <div className="dash-llm-badge">
                        <span className="dash-llm-badge-key">Niveau</span>
                        <span className="dash-llm-badge-val">{llmData.niveau_profil}</span>
                      </div>
                      <div className="dash-llm-badge">
                        <span className="dash-llm-badge-key">Parcours</span>
                        <span className="dash-llm-badge-val">{llmData.type_parcours}</span>
                      </div>
                      <div className="dash-llm-badge">
                        <span className="dash-llm-badge-key">Mobilité</span>
                        <span className="dash-llm-badge-val">{llmData.mobilite_geographique}</span>
                      </div>
                      <div className="dash-llm-badge">
                        <span className="dash-llm-badge-key">Autonomie</span>
                        <span className="dash-llm-badge-val">{llmData.hs_autonomie_technique}</span>
                      </div>
                      <div className="dash-llm-badge">
                        <span className="dash-llm-badge-key">Impact</span>
                        <span className="dash-llm-badge-val">{llmData.impact_ampleur}</span>
                      </div>
                      <div className="dash-llm-badge">
                        <span className="dash-llm-badge-key">Progression</span>
                        <span className="dash-llm-badge-val">{llmData.progression_technique}</span>
                      </div>
                    </div>
                  ) : (
                    <p style={{color:"var(--t3)",fontSize:13}}>Évaluation IA non disponible.</p>
                  )}
                </div>
              </div>

              {/* row 3 : skills + anomalies */}
              <div className="dash-grid-2">
                <div className="dash-panel">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Compétences détectées</span>
                    <span style={{fontSize:11,color:"var(--t3)"}}>{skillsList.length} skills</span>
                  </div>
                  {skillsList.length > 0 ? (
                    <div className="dash-skills-cloud">
                      {skillsList.map((s, i) => (
                        <span key={i} className={`dash-skill-tag${i%3===0?"":" dash-skill-tag--neutral"}`}>
                          {s.skill_name || s}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p style={{color:"var(--t3)",fontSize:13}}>Aucune compétence enregistrée.</p>
                  )}
                </div>

                <div className="dash-panel">
                  <div className="dash-panel-head">
                    <span className="dash-panel-title">Alertes IA</span>
                    <AlertTriangle size={14} color={anomalies.some(a=>a.val) ? "var(--cr)" : "#4ade80"}/>
                  </div>
                  {anomalies.length > 0 ? (
                    <div className="dash-anomaly-list">
                      {anomalies.map(a => (
                        <div key={a.key} className={`dash-anomaly-item dash-anomaly-item--${a.val?"bad":"ok"}`}>
                          <div className="dash-anomaly-dot"/>
                          <span>{a.key}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{color:"var(--t3)",fontSize:13}}>Évaluation IA non disponible.</p>
                  )}
                </div>
              </div>

              {/* recent applications */}
              {applications.length > 0 && (
                <div className="dash-recent-panel">
                  <div className="dash-recent-head">
                    <span className="dash-recent-title">Candidatures récentes</span>
                    <button type="button" className="dash-recent-link" onClick={() => setActive("candidatures")}>Voir tout →</button>
                  </div>
                  {applications.slice(0,5).map(app => {
                    const st = (app.status||"").toUpperCase();
                    const sl = st==="ACCEPTEE"?"Acceptée":st==="REFUSEE"?"Refusée":"En cours";
                    const sc = st==="ACCEPTEE"?"accepted":st==="REFUSEE"?"refused":"pending";
                    const dt = app.validatedAt ? new Date(app.validatedAt).toLocaleDateString("fr-FR",{day:"2-digit",month:"short"}) : "-";
                    return (
                      <div className="dash-recent-row" key={app.id}>
                        <div>
                          <div className="dash-recent-title-job">{app.jobTitle||"Poste non renseigné"}</div>
                          {app.company && <div className="dash-recent-company">{app.company}</div>}
                        </div>
                        <span className={`dash-status-pill dash-status-pill--${sc}`}>{sl}</span>
                        <div className="dash-recent-date">{dt}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════
              PORTFOLIO COURT
          ═══════════════════════════════════ */}
          {active === "portfolio" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Portfolio Court</h1>
                <p className="dash-page-sub">Vos réalisations condensées · fichiers PDF et projets</p>
              </div>
              <div className="portfolio-shell">
                {portfolioShort.length === 0 && portfolio.length === 0 ? (
                  <div className="dash-section-card"><p>Aucun portfolio court disponible.</p></div>
                ) : (
                  <>
                    {portfolioShort.length > 0 && renderFiles(portfolioShort, "")}
                    {portfolio.length > 0 && (
                      <div className="pf-grid">
                        {portfolio.map((item, i) => {
                          const tags = Array.isArray(item.tags) ? item.tags : [];
                          const desc = item.shortDescription || (item.longDescription ? `${item.longDescription.slice(0,140)}…` : "");
                          return (
                            <div className="pf-card" key={item.id}>
                              <div className="pf-thumb">
                                <div className="pf-thumb-bg" style={{background:GRADIENTS[i%GRADIENTS.length]}}/>
                                <div className="pf-thumb-overlay"/>
                                <span className="pf-thumb-num">{String(i+1).padStart(2,"0")}</span>
                              </div>
                              <div className="pf-body">
                                <div className="pf-title">{item.title}</div>
                                <div className="pf-desc">{desc}</div>
                                <div className="pf-tags">{tags.map(t=><span className="pf-tag" key={t}>{t}</span>)}</div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════
              PORTFOLIO LONG
          ═══════════════════════════════════ */}
          {active === "portfolio-long" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Portfolio Long</h1>
                <p className="dash-page-sub">Description complète de vos projets · {portfolio.length} travaux</p>
              </div>
              <div className="portfolio-shell">
                {portfolioLong.length === 0 && portfolio.length === 0 ? (
                  <div className="dash-section-card"><p>Aucun portfolio long disponible.</p></div>
                ) : (
                  <>
                    {portfolioLong.length > 0 && renderFiles(portfolioLong, "")}
                    {portfolio.length > 0 && (
                      <div className="pf-list">
                        {portfolio.map((item, i) => {
                          const tags = Array.isArray(item.tags) ? item.tags : [];
                          const date = item.createdAt ? new Date(item.createdAt).toLocaleDateString("fr-FR",{year:"numeric",month:"short"}) : "";
                          const desc = item.longDescription || item.shortDescription || "";
                          return (
                            <div className="pf-row" key={item.id}>
                              <div className="pf-row-thumb">
                                <div className="pf-row-thumb-bg" style={{background:GRADIENTS[i%GRADIENTS.length]}}/>
                              </div>
                              <div className="pf-row-info">
                                <div className="pf-row-title">{item.title}</div>
                                <div className="pf-row-desc">{desc}</div>
                                <div className="pf-tags">{tags.map(t=><span className="pf-tag" key={t}>{t}</span>)}</div>
                              </div>
                              <div className="pf-row-meta">
                                <span className="pf-row-date">{date}</span>
                                <ArrowRight size={13} className="pf-row-arrow"/>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════
              BIENVENUE (wizard)
          ═══════════════════════════════════ */}
          {active === "fichiers" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Bienvenue</h1>
                <p className="dash-page-sub">Créez votre profil professionnel étape par étape avec l'IA.</p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  {/* wizard progress */}
                  <div className="welcome-wizard-steps">
                    {wizardSteps.map((step, idx) => (
                      <React.Fragment key={step.id}>
                        <div className={`wizard-step-circle wizard-step-circle--${currentWizardStep===step.id?"active":currentWizardStep>step.id?"done":"inactive"}`}>
                          {currentWizardStep>step.id?"✓":step.id}
                        </div>
                        {idx < wizardSteps.length-1 && (
                          <div className={`wizard-step-line wizard-step-line--${currentWizardStep>step.id?"done":"undone"}`}/>
                        )}
                      </React.Fragment>
                    ))}
                  </div>

                  {/* AI bubble */}
                  <div className="wizard-ai-box">
                    <div className="wizard-ai-inner">
                      <div className="wizard-ai-avatar"><img src={logo} alt="TAP"/></div>
                      <div style={{flex:1}}>
                        <div className="wizard-ai-title">{currentStepData.title}</div>
                        <p className="wizard-ai-msg">{currentStepData.aiMessage}</p>
                        <div className="wizard-ai-info">
                          <p>{currentStepData.aiExplanation}</p>
                          <p>{currentStepData.whatAiDoes}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {wizardError && <div className="wizard-error-box">{wizardError}</div>}

                  <form onSubmit={handleWizardSubmit} className="contact-form">
                    {currentWizardStep === 1 && (
                      <>
                        <div className="form-row">
                          <div className="form-field">
                            <label>Nationalité <span style={{color:"var(--cr)"}}>*</span></label>
                            <input type="text" value={nationality} onChange={e=>setNationality(e.target.value)} placeholder="Ex: Marocaine, Française…" required/>
                          </div>
                          <div className="form-field">
                            <label>Pays de résidence <span style={{color:"var(--cr)"}}>*</span></label>
                            <input type="text" value={locationCountry} onChange={e=>setLocationCountry(e.target.value)} placeholder="Ex: Maroc, France…" required/>
                          </div>
                        </div>
                        <div className="form-row">
                          <div className="form-field">
                            <label>Niveau de séniorité <span style={{color:"var(--cr)"}}>*</span></label>
                            <select value={seniorityLevel} onChange={e=>setSeniorityLevel(e.target.value)} required>
                              <option value="">Sélectionner…</option>
                              <option value="Entry Level">Entry Level / Débutant</option>
                              <option value="Junior">Junior</option>
                              <option value="Intermediate">Intermédiaire</option>
                              <option value="Mid-Level">Mid-Level / Confirmé</option>
                              <option value="Senior">Senior</option>
                              <option value="Expert">Expert / Lead</option>
                            </select>
                          </div>
                          <div className="form-field">
                            <label>Disponibilité <span style={{color:"var(--cr)"}}>*</span></label>
                            <select value={disponibilite} onChange={e=>setDisponibilite(e.target.value)} required>
                              <option value="">Sélectionner…</option>
                              <option value="Immediat">Immédiate</option>
                              <option value="1 semaine">1 semaine</option>
                              <option value="2 semaines">2 semaines</option>
                              <option value="3 semaines">3 semaines</option>
                              <option value="4 semaines">4 semaines</option>
                              <option value="5 semaines">5 semaines</option>
                            </select>
                          </div>
                        </div>
                        <div className="form-field">
                          <label>Photo professionnelle <span style={{color:"var(--cr)"}}>*</span></label>
                          <input type="file" accept=".jpg,.jpeg,.png" onChange={e=>setImgFile(e.target.files?.[0]||null)}/>
                          {imgFile && (
                            <div className="login-error" style={{marginTop:6}}>
                              ✅ <span style={{marginLeft:6}}>{imgFile.name}</span>
                              <button type="button" onClick={()=>setImgFile(null)} style={{marginLeft:10,color:"var(--cr)",background:"none",border:"none",cursor:"pointer",textDecoration:"underline"}}>Supprimer</button>
                            </div>
                          )}
                        </div>
                      </>
                    )}

                    {currentWizardStep === 2 && (
                      <>
                        <div className="form-row">
                          <div className="form-field">
                            <label>Poste cible <span style={{color:"var(--cr)"}}>*</span></label>
                            <input type="text" value={targetPosition} onChange={e=>setTargetPosition(e.target.value)} placeholder="Ex: Data Scientist…" required/>
                          </div>
                          <div className="form-field">
                            <label>Pays cible <span style={{color:"var(--cr)"}}>*</span></label>
                            <input type="text" value={targetCountry} onChange={e=>setTargetCountry(e.target.value)} placeholder="Ex: France, Canada…" required/>
                          </div>
                        </div>
                        <div className="form-row">
                          <div className="form-field">
                            <label>Prêt à relocaliser</label>
                            <select value={pretARelocater} onChange={e=>setPretARelocater(e.target.value)}>
                              <option value="">Non spécifié</option>
                              <option value="Oui">Oui</option>
                              <option value="Non">Non</option>
                            </select>
                          </div>
                          <div className="form-field">
                            <label>Salaire minimum <span style={{color:"var(--cr)"}}>*</span></label>
                            <input type="text" value={salaireMinimum} onChange={e=>setSalaireMinimum(e.target.value)} placeholder="Ex: 50000" required/>
                          </div>
                        </div>
                        <div className="form-field">
                          <label>Exigences / Pré-requis <span style={{color:"var(--cr)"}}>*</span></label>
                          <textarea value={constraints} onChange={e=>setConstraints(e.target.value)} rows={3} required/>
                        </div>
                        <div className="form-field">
                          <label>Ce que tu recherches <span style={{color:"var(--cr)"}}>*</span></label>
                          <textarea value={searchCriteria} onChange={e=>setSearchCriteria(e.target.value)} rows={3} required/>
                        </div>
                        <div className="form-field">
                          <label>Types de contrat <span style={{color:"var(--cr)"}}>*</span></label>
                          <div style={{display:"flex",gap:16,flexWrap:"wrap"}}>
                            {["CDI","CDD","Freelance","Mission","Stage"].map(type => (
                              <label key={type} style={{display:"flex",alignItems:"center",gap:6,cursor:"pointer",fontSize:13,color:"var(--t2)"}}>
                                <input type="checkbox" value={type} checked={typeContrat.includes(type)}
                                  onChange={e => setTypeContrat(p => e.target.checked ? [...p,type] : p.filter(t=>t!==type))}/>
                                {type}
                              </label>
                            ))}
                          </div>
                        </div>
                        <div className="form-field">
                          <label>Domaine d'activité <span style={{color:"var(--cr)"}}>*</span></label>
                          <input type="text" value={domaineActivite} onChange={e=>setDomaineActivite(e.target.value)} placeholder="Ex: Intelligence artificielle & Data" required/>
                        </div>
                      </>
                    )}

                    {currentWizardStep === 3 && (
                      <>
                        <div className="form-row">
                          <div className="form-field">
                            <label>CV (PDF ou DOCX)</label>
                            <input type="file" accept=".pdf,.doc,.docx" onChange={e=>setCvFile(e.target.files?.[0]||null)}/>
                            {cvFile && (
                              <div className="login-error" style={{marginTop:6}}>
                                ✅ <span style={{marginLeft:6}}>{cvFile.name}</span>
                                <button type="button" onClick={()=>setCvFile(null)} style={{marginLeft:10,color:"var(--cr)",background:"none",border:"none",cursor:"pointer",textDecoration:"underline"}}>Supprimer</button>
                              </div>
                            )}
                          </div>
                          <div className="form-field">
                            <label>OU URL LinkedIn</label>
                            <input type="url" value={linkedinUrl} onChange={e=>setLinkedinUrl(e.target.value)} placeholder="https://www.linkedin.com/in/…"/>
                          </div>
                        </div>
                        <div className="form-field">
                          <label>URL GitHub</label>
                          <input type="url" value={githubUrl} onChange={e=>setGithubUrl(e.target.value)} placeholder="https://github.com/…"/>
                        </div>
                      </>
                    )}

                    {currentWizardStep === 4 && (
                      <div style={{textAlign:"center",padding:"10px 0"}}>
                        <p style={{color:"var(--t2)",marginBottom:14}}>✅ Ton profil est complet !</p>
                        <p style={{fontSize:13,color:"var(--t3)",marginBottom:14}}>Choisis la langue de ta Talent Card :</p>
                        <div className="talentcard-lang-toggle">
                          <button type="button" className={`talentcard-lang-btn talentcard-lang-btn--${talentCardLang==="fr"?"active":"inactive"}`} onClick={()=>setTalentCardLangAndSave("fr")}>FR</button>
                          <button type="button" className={`talentcard-lang-btn talentcard-lang-btn--${talentCardLang==="en"?"active":"inactive"}`} onClick={()=>setTalentCardLangAndSave("en")}>EN</button>
                        </div>
                        <p style={{fontSize:13,color:"var(--t3)"}}>Cliquez sur "Générer" pour lancer le traitement IA.</p>
                      </div>
                    )}

                    <div className="contact-submit-wrapper" style={{justifyContent:"space-between"}}>
                      <div>
                        {currentWizardStep > 1 && (
                          <button type="button" className="contact-submit" onClick={()=>setCurrentWizardStep(s=>s-1)}
                            style={{background:"transparent",border:"1px solid rgba(202,27,40,0.4)",color:"var(--cr)"}}>
                            ← Précédent
                          </button>
                        )}
                      </div>
                      <div>
                        {currentWizardStep < 4 ? (
                          <button type="button" className="contact-submit" disabled={!isStepComplete(currentWizardStep)}
                            onClick={()=>isStepComplete(currentWizardStep)&&setCurrentWizardStep(s=>s+1)}>
                            Suivant →
                          </button>
                        ) : (
                          <button type="submit" className="contact-submit"
                            disabled={wizardLoading||!isStepComplete(1)||!isStepComplete(2)||!isStepComplete(3)}>
                            {wizardLoading ? "Génération en cours…" : "🚀 Générer ma Talent Card"}
                          </button>
                        )}
                      </div>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════
              CV
          ═══════════════════════════════════ */}
          {active === "cv" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Mes CV</h1>
                <p className="dash-page-sub">Gérez plusieurs versions de CV et consultez les statistiques en temps réel.</p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  <div className="files-upload-bar">
                    <label className="files-upload-btn">
                      {uploadingCv ? "Import en cours…" : "+ Importer un nouveau CV"}
                      <input type="file" accept="application/pdf" onChange={handleUploadCv} disabled={uploadingCv}/>
                    </label>
                    <p className="files-upload-hint">Formats acceptés : PDF. Stockage sécurisé TAP.</p>
                  </div>
                  {uploadErrorCv && <div className="login-error" style={{marginBottom:12}}>⚠ {uploadErrorCv}</div>}
                  {cvFiles.length === 0
                    ? <p>Aucun CV enregistré pour l'instant.</p>
                    : <div className="files-list">
                        {cvFiles.map(file => {
                          const date   = file.updatedAt ? new Date(file.updatedAt).toLocaleDateString("fr-FR",{year:"numeric",month:"short",day:"2-digit"}) : "-";
                          const sizeKb = typeof file.size==="number" ? Math.round(file.size/1024) : null;
                          return (
                            <div className="files-row" key={file.path}>
                              <div className="files-main">
                                <div className="files-name">{file.name}</div>
                                <div className="files-meta"><span>{date}</span>{sizeKb!==null&&<span>· {sizeKb} Ko</span>}</div>
                              </div>
                              <div className="files-actions">
                                <a href={file.publicUrl} target="_blank" rel="noopener noreferrer" className="files-btn">Télécharger</a>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                  }
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════
              TALENT CARD
          ═══════════════════════════════════ */}
          {active === "talentcard" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Talent Card</h1>
                <p className="dash-page-sub">Vos Talent Cards générées (PDF).</p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  {talentcardFiles.length === 0
                    ? <p>Aucune Talent Card PDF enregistrée pour le moment.</p>
                    : renderFiles(talentcardFiles, "")
                  }
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════
              CANDIDATURES
          ═══════════════════════════════════ */}
          {active === "candidatures" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Mes candidatures</h1>
                <p className="dash-page-sub">Suivez le statut de chacune de vos candidatures.</p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  {applications.length === 0
                    ? <p>Aucune candidature enregistrée pour le moment.</p>
                    : <div className="cand-list">
                        {applications.map(app => {
                          const st = (app.status||"").toUpperCase();
                          const sl = st==="ACCEPTEE"?"Acceptée":st==="REFUSEE"?"Refusée":"En cours";
                          const sc = st==="ACCEPTEE"?"accepted":st==="REFUSEE"?"refused":"pending";
                          const dt = app.validatedAt ? new Date(app.validatedAt).toLocaleDateString("fr-FR",{year:"numeric",month:"short",day:"2-digit"}) : "-";
                          return (
                            <div className="cand-row" key={app.id}>
                              <div className="cand-job">
                                <div className="cand-job-title">{app.jobTitle||"Poste non renseigné"}</div>
                                {app.company && <div className="cand-job-company">{app.company}</div>}
                              </div>
                              <div className="cand-status"><span className={`cand-status-pill cand-status-pill--${sc}`}>{sl}</span></div>
                              <div className="cand-date">{dt}</div>
                            </div>
                          );
                        })}
                      </div>
                  }
                </div>
              </div>
            </div>
          )}

          {/* ═══════════════════════════════════
              ENTRETIENS + fallback
          ═══════════════════════════════════ */}
          {active === "entretiens" && (
            <div className="dash-content">
              <div className="dash-page-header">
                <h1 className="dash-page-title">Entretiens</h1>
                <p className="dash-page-sub">Gérez et organisez votre espace personnel</p>
              </div>
              <div className="dash-section-page">
                <div className="dash-section-card">
                  <p>Historique de vos entretiens passés, prochaines étapes et rappels automatiques pour ne rien manquer.</p>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </section>
  );
}
