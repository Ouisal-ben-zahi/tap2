import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import heroImage from "../assets/new-bgpages.jpg";
import "../css/Connexion.css";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

/* ── small SVG icons (inline, no extra dep) ── */
const IconUser    = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>;
const IconLock    = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>;
const IconStar    = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>;
const IconBolt    = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>;
const IconShield  = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
const IconEye     = ({ open }) => open
  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>
  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>;

function Connexion() {
  const navigate = useNavigate();
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [showPwd,     setShowPwd]     = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Email et mot de passe sont obligatoires.");
      return;
    }

    setLoading(true);
    try {
      const res  = await fetch(`${API_BASE}/auth/login`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim(), password }),
        credentials: "include",
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data.message || "Identifiants incorrects.");
        return;
      }

      const userRole  = data.role  || data.user?.role;
      const userEmail = data.email || data.user?.email || email.trim();
      const userId    = data.id    || data.user?.id;

      if (data.token)  sessionStorage.setItem("authToken",    data.token);
      if (userRole)    sessionStorage.setItem("profileType",  userRole);
      if (userEmail)   sessionStorage.setItem("userEmail",    userEmail);
      if (userId)      sessionStorage.setItem("userId",       String(userId));

      navigate(userRole === "recruteur" ? "/dashboard-recruteur" : "/dashboard-candidat");
    } catch {
      setError("Erreur de connexion au serveur.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="login-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="login-inner">

        {/* ── LEFT: brand + features ── */}
        <div className="login-left">
          <div className="login-brand">
            <span className="login-brand-tag">Plateforme de talents</span>
            <h1 className="login-brand-name">
              Talent<span>.</span>
            </h1>
            <p className="login-brand-desc">
              La plateforme de référence pour connecter les talents d'exception
              avec les opportunités qui les méritent.
            </p>
          </div>

          <div className="login-features">
            <div className="login-feature">
              <div className="login-feature-dot" style={{ color: "#ef4444" }}>
                <IconStar />
              </div>
              <div className="login-feature-text">
                <strong>Profil Premium</strong>
                <span>Valorisez vos compétences avec votre Talent Card personnalisée</span>
              </div>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" style={{ color: "#ef4444" }}>
                <IconBolt />
              </div>
              <div className="login-feature-text">
                <strong>Matching Intelligent</strong>
                <span>Soyez mis en relation avec les offres qui correspondent à votre profil</span>
              </div>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" style={{ color: "#ef4444" }}>
                <IconShield />
              </div>
              <div className="login-feature-text">
                <strong>Données Sécurisées</strong>
                <span>Vos informations sont chiffrées et protégées en permanence</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── RIGHT: form ── */}
        <div className="login-right">
          <header className="login-header">
            <span className="login-badge">Espace membre</span>
            <h2 className="login-heading-main">Connexion à votre compte</h2>
            <p className="login-heading-sub">Accédez à votre espace TAP en toute sécurité.</p>
          </header>

          <form className="login-form" onSubmit={handleSubmit} noValidate>

            {/* email */}
            <div className="login-field">
              <label htmlFor="login-email">Adresse e-mail</label>
              <input
                id="login-email"
                type="email"
                placeholder="vous@exemple.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>

            {/* password */}
            <div className="login-field">
              <label htmlFor="login-password">Mot de passe</label>
              <div className="password-input-wrapper">
                <input
                  id="login-password"
                  className="password-input"
                  type={showPwd ? "text" : "password"}
                  placeholder="Votre mot de passe"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className={`password-eye${showPwd ? " password-eye--active" : ""}`}
                  onClick={() => setShowPwd(p => !p)}
                  aria-label={showPwd ? "Masquer" : "Afficher"}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    color: showPwd ? "#ef4444" : "#475569",
                  }}
                >
                  <IconEye open={showPwd} />
                </button>
              </div>
            </div>

            {/* error */}
            {error && (
              <div className="login-error">
                <span>⚠</span> {error}
              </div>
            )}

            {/* submit */}
            <div className="login-submit-wrapper">
              <button type="submit" className="login-submit" disabled={loading}>
                {loading ? "Connexion en cours…" : "Se connecter"}
              </button>

              <div className="login-footer-links">
                <button
                  type="button"
                  className="login-link"
                  onClick={() => { /* TODO: navigate to reset */ }}
                >
                  Mot de passe oublié ?
                </button>
                <button
                  type="button"
                  className="login-link login-link--accent"
                  onClick={() => navigate("/creer-compte")}
                >
                  Créer un compte →
                </button>
              </div>
            </div>

          </form>

          {/* subtle divider + tagline */}
          <div className="login-divider">Plateforme sécurisée</div>
        </div>

      </div>
    </section>
  );
}

export default Connexion;
