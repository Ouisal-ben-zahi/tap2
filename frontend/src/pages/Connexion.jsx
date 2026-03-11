import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import heroImage from "../assets/new-bgpages.jpg";
import "../css/Connexion.css";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

/* ── small SVG icons (inline, no extra dep) ── */
const IconStar    = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>;
const IconBolt    = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>;
const IconShield  = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
const IconMail    = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
    <polyline points="22,6 12,13 2,6"/>
  </svg>
);
const IconLock    = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <rect x="4" y="10" width="16" height="10" rx="2" />
    <path d="M8 10V7a4 4 0 0 1 8 0v3" />
  </svg>
);
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
  const [resetMode,   setResetMode]   = useState(false);
  const [resetStep,   setResetStep]   = useState(1);
  const [resetEmail,  setResetEmail]  = useState("");
  const [resetCode,   setResetCode]   = useState("");
  const [resetNewPwd, setResetNewPwd] = useState("");
  const [resetLoading,setResetLoading]= useState(false);
  const [resetMsg,    setResetMsg]    = useState("");
  const [resetError,  setResetError]  = useState("");

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

  const handleRequestReset = async (e) => {
    e.preventDefault();
    setResetError("");
    setResetMsg("");

    const targetEmail = resetEmail.trim() || email.trim();
    if (!targetEmail) {
      setResetError("Merci de renseigner votre adresse e-mail.");
      return;
    }

    setResetLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/request-password-reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: targetEmail }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setResetError(data.message || "Erreur lors de l’envoi du code.");
        return;
      }
      setResetEmail(targetEmail);
      setResetMsg(
        data.message ||
        "Si un compte existe pour cet email, un code de réinitialisation a été envoyé."
      );
      setResetStep(2);
    } catch {
      setResetError("Erreur de connexion au serveur.");
    } finally {
      setResetLoading(false);
    }
  };

  const handleConfirmReset = async (e) => {
    e.preventDefault();
    setResetError("");
    setResetMsg("");

    if (!resetEmail.trim() || !resetCode.trim() || !resetNewPwd.trim()) {
      setResetError("Email, code et nouveau mot de passe sont obligatoires.");
      return;
    }
    if (resetNewPwd.length < 8) {
      setResetError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }

    setResetLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: resetEmail.trim(),
          code: resetCode.trim(),
          newPassword: resetNewPwd,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setResetError(data.message || "Code invalide ou expiré.");
        return;
      }

      setResetMsg(data.message || "Votre mot de passe a été réinitialisé.");
      // Pré-remplir l’email de connexion et revenir au formulaire de login
      setEmail(resetEmail.trim());
      setPassword("");
      setResetMode(false);
      setResetStep(1);
      setResetCode("");
      setResetNewPwd("");
    } catch {
      setResetError("Erreur de connexion au serveur.");
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <section
      className="login-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="login-inner">

        {/* ── LEFT: titre + features ── */}
        <div className="login-left">
          <div className="login-left-header">
            <span className="login-left-tag">Espace sécurisé</span>
            <h1 className="login-left-title">
              Connectez-vous à <span className="login-left-title-tap">TAP</span>
            </h1>
            <p className="login-left-desc">
              Accédez à votre espace candidat ou recruteur, suivez vos candidatures
              et retrouvez vos offres en un seul endroit.
            </p>
          </div>

          <div className="login-features">
            <div className="login-feature">
              <div className="login-feature-dot" style={{ color: "#ef4444" }}>
                <IconStar />
              </div>
              <div className="login-feature-text">
                <strong>Accès instantané</strong>
                <span>Retrouvez vos tableaux de bord candidats et recruteurs en un clic.</span>
              </div>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" style={{ color: "#ef4444" }}>
                <IconBolt />
              </div>
              <div className="login-feature-text">
                <strong>Connexion fluide</strong>
                <span>Une interface pensée pour aller droit à l’essentiel, sans friction.</span>
              </div>
            </div>
            <div className="login-feature">
              <div className="login-feature-dot" style={{ color: "#ef4444" }}>
                <IconShield />
              </div>
              <div className="login-feature-text">
                <strong>Données protégées</strong>
                <span>Vos informations sont chiffrées et sécurisées en permanence.</span>
              </div>
            </div>
          </div>
        </div>

        {/* ── RIGHT: form ── */}
        <div className="login-right">
          <header className="login-header">
            <span className="login-badge">Espace membre</span>
            <h2 className="login-heading-main">
              {resetMode ? "Réinitialiser votre mot de passe" : "Connexion à votre compte"}
            </h2>
            <p className="login-heading-sub">
              {resetMode
                ? "Recevez un code par email puis choisissez un nouveau mot de passe."
                : "Accédez à votre espace TAP en toute sécurité."}
            </p>
          </header>

          {!resetMode && (
            <form className="login-form" onSubmit={handleSubmit} noValidate>

            {/* email */}
            <div className="login-field">
              <label htmlFor="login-email">Adresse e-mail</label>
              <div className="login-input-with-icon">
                <span className="login-input-icon">
                  <IconMail />
                </span>
                <input
                  id="login-email"
                  type="email"
                  className="login-input-leading"
                  placeholder="vous@exemple.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            {/* password */}
            <div className="login-field">
              <label htmlFor="login-password">Mot de passe</label>
              <div className="password-input-wrapper">
                <span className="login-input-icon">
                  <IconLock />
                </span>
                <input
                  id="login-password"
                  className="password-input login-input-leading"
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
                  onClick={() => {
                    setResetMode(true);
                    setResetStep(1);
                    setResetEmail(email);
                    setResetError("");
                    setResetMsg("");
                  }}
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
          )}

          {resetMode && (
            <form
              className="login-form"
              onSubmit={resetStep === 1 ? handleRequestReset : handleConfirmReset}
              noValidate
            >
              {/* email */}
              <div className="login-field">
                <label htmlFor="reset-email">Adresse e-mail</label>
                <input
                  id="reset-email"
                  type="email"
                  placeholder="vous@exemple.com"
                  value={resetEmail}
                  onChange={e => setResetEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>

              {/* step 1 : demande code */}
              {resetStep === 1 && (
                <p className="login-heading-sub">
                  Nous vous enverrons un code à 6 chiffres à cette adresse si un compte existe.
                </p>
              )}

              {/* step 2 : code + nouveau mot de passe */}
              {resetStep === 2 && (
                <>
                  <div className="login-field">
                    <label htmlFor="reset-code">Code reçu par email</label>
                    <input
                      id="reset-code"
                      type="text"
                      placeholder="123456"
                      value={resetCode}
                      onChange={e => setResetCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    />
                  </div>

                  <div className="login-field">
                    <label htmlFor="reset-password">Nouveau mot de passe</label>
                    <input
                      id="reset-password"
                      type="password"
                      placeholder="Minimum 8 caractères"
                      value={resetNewPwd}
                      onChange={e => setResetNewPwd(e.target.value)}
                      minLength={8}
                      required
                    />
                  </div>
                </>
              )}

              {/* error / message */}
              {resetError && (
                <div className="login-error">
                  <span>⚠</span> {resetError}
                </div>
              )}
              {resetMsg && !resetError && (
                <div className="login-error" style={{ borderColor: "rgba(34,197,94,0.4)", background: "rgba(22,163,74,0.12)", color: "#bbf7d0" }}>
                  {resetMsg}
                </div>
              )}

              <div className="login-submit-wrapper">
                <button type="submit" className="login-submit" disabled={resetLoading}>
                  {resetLoading
                    ? "Traitement…"
                    : resetStep === 1
                      ? "Envoyer le code"
                      : "Confirmer le nouveau mot de passe"}
                </button>

                <div className="login-footer-links">
                  <button
                    type="button"
                    className="login-link"
                    onClick={() => {
                      setResetMode(false);
                      setResetStep(1);
                      setResetEmail("");
                      setResetCode("");
                      setResetNewPwd("");
                      setResetError("");
                      setResetMsg("");
                    }}
                  >
                    ← Retour à la connexion
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
          )}

          {/* subtle divider + tagline */}
          <div className="login-divider">Plateforme sécurisée</div>
        </div>

      </div>
    </section>
  );
}

export default Connexion;
