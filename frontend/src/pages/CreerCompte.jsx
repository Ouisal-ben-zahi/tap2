import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import heroImage from "../assets/new-bgpages.jpg";
import "../css/Signup.css";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

/* ── inline SVG icons ─────────────────────────── */
const IconBriefcase = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <rect x="2" y="7" width="20" height="14" rx="2"/>
    <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
    <line x1="12" y1="12" x2="12" y2="12"/>
  </svg>
);

const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <circle cx="11" cy="11" r="8"/>
    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
);

const IconEye = ({ open }) => open
  ? <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></svg>
  : <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>;

const IconCheck = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const IconMail = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
    <polyline points="22,6 12,13 2,6"/>
  </svg>
);

const IconLock = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <rect x="4" y="10" width="16" height="10" rx="2" />
    <path d="M8 10V7a4 4 0 0 1 8 0v3" />
  </svg>
);

/* ── steps config ─────────────────────────────── */
const STEPS = [
  { n: "01", title: "Choisir un profil",    desc: "Candidat à la recherche d'opportunités ou recruteur en quête de talents." },
  { n: "02", title: "Renseigner vos infos", desc: "Votre adresse e-mail et un mot de passe sécurisé suffisent pour commencer." },
  { n: "03", title: "Vérification e-mail",  desc: "Un code à 6 chiffres vous est envoyé pour confirmer votre identité." },
];

/* ═══════════════════════════════════════════════ */
function CreerCompte() {
  const navigate = useNavigate();

  const [accountType,       setAccountType]       = useState("candidat");
  const [email,             setEmail]             = useState("");
  const [password,          setPassword]          = useState("");
  const [confirmPassword,   setConfirmPassword]   = useState("");
  const [showPwd,           setShowPwd]           = useState(false);
  const [loading,           setLoading]           = useState(false);
  const [error,             setError]             = useState("");
  const [verificationSent,  setVerificationSent]  = useState(false);
  const [verifyMsg,         setVerifyMsg]         = useState("");
  const [code,              setCode]              = useState("");

  /* current step for left panel highlight */
  const currentStep = verificationSent ? 2 : 1;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    /* ── STEP 2: verify code ── */
    if (verificationSent) {
      if (!code.trim()) return;
      setLoading(true);
      try {
        const res  = await fetch(`${API_BASE}/auth/verify-and-register`, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ email, code: code.trim() }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { setError(data.message || "Code invalide ou expiré."); return; }
        sessionStorage.setItem("profileType", data.role);
        sessionStorage.setItem("userEmail",   data.email);
        navigate("/connexion", { replace: true });
      } catch {
        setError("Erreur de connexion au serveur.");
      } finally {
        setLoading(false);
      }
      return;
    }

    /* ── STEP 1: send code ── */
    if (!email.trim() || !password.trim() || !confirmPassword.trim()) {
      setError("Merci de remplir tous les champs.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Les deux mots de passe ne correspondent pas.");
      return;
    }
    setLoading(true);
    try {
      const res  = await fetch(`${API_BASE}/auth/send-verification`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim(), password, role: accountType }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { setError(data.message || "Erreur lors de l'envoi du code."); return; }
      setVerifyMsg(data.message || "");
      setVerificationSent(true);
    } catch {
      setError("Erreur de connexion au serveur.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="signup-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="signup-inner">

        {/* ══ LEFT: titre + tag + steps ══ */}
        <div className="signup-left">
          <div className="signup-left-header">
            <span className="signup-left-tag">Expérience premium</span>
            <h2 className="signup-left-title">
              Créez votre profil <span className="signup-left-title-tap">TAP</span>
            </h2>
            <p className="signup-left-desc">
              Une seule inscription pour accéder à votre espace candidat ou recruteur,
              gérer vos dossiers et suivre vos opportunités.
            </p>
          </div>

          <div className="signup-steps">
            {STEPS.map(({ n, title, desc }, i) => {
              const done    = i < currentStep;
              const active  = i === currentStep;
              return (
                <div className="signup-step" key={n}>
                  <div className={`signup-step-num${done ? " signup-step-num--done" : ""}`}>
                    {done ? <IconCheck /> : n}
                  </div>
                  <div className="signup-step-body">
                    <strong style={{ color: active ? "#f1f5f9" : done ? "#94a3b8" : "#475569" }}>
                      {title}
                    </strong>
                    <span>{desc}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ══ RIGHT: form ══ */}
        <div className="signup-right">
          <header className="signup-header">
            <p className="signup-badge">Inscription gratuite</p>
            <h2 className="signup-heading">
              {verificationSent ? "Vérifiez votre e-mail" : "Créer votre compte"}
            </h2>
            <p className="signup-subheading">
              {verificationSent
                ? `Un code a été envoyé à ${email}`
                : "Rejoignez des milliers de talents et recruteurs."}
            </p>
          </header>

          <form className="signup-form" onSubmit={handleSubmit} noValidate>

            {/* ── STEP 1 ── */}
            {!verificationSent && (
              <>
                {/* account type – sous forme de champs avec icône */}
                <div className="signup-type-group">
                  <span className="signup-type-label">Vous êtes</span>
                  <div className="signup-type-inputs">
                    <button
                      type="button"
                      className={`signup-type-input${accountType === "candidat" ? " signup-type-input--active" : ""}`}
                      onClick={() => setAccountType("candidat")}
                    >
                      <span className="signup-type-input-icon">
                        <IconSearch />
                      </span>
                      <div className="signup-type-input-text">
                        <span className="signup-type-input-main">Je suis candidat</span>
                        <span className="signup-type-input-sub">Je cherche des opportunités</span>
                      </div>
                    </button>
                    <button
                      type="button"
                      className={`signup-type-input${accountType === "recruteur" ? " signup-type-input--active" : ""}`}
                      onClick={() => setAccountType("recruteur")}
                    >
                      <span className="signup-type-input-icon">
                        <IconBriefcase />
                      </span>
                      <div className="signup-type-input-text">
                        <span className="signup-type-input-main">Je suis recruteur</span>
                        <span className="signup-type-input-sub">Je recrute des talents</span>
                      </div>
                    </button>
                  </div>
                </div>

                {/* email */}
                <div className="signup-field">
                  <label htmlFor="signup-email">Adresse e-mail</label>
                  <div className="signup-input-with-icon">
                    <span className="signup-input-icon">
                      <IconMail />
                    </span>
                    <input
                      id="signup-email"
                      type="email"
                      className="signup-input-leading"
                      placeholder="vous@exemple.com"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      autoComplete="email"
                      required
                    />
                  </div>
                </div>

                {/* password */}
                <div className="signup-field">
                  <label htmlFor="signup-password">Mot de passe</label>
                  <div className="password-input-wrapper">
                    <span className="signup-input-icon">
                      <IconLock />
                    </span>
                    <input
                      id="signup-password"
                      className="password-input signup-input-leading"
                      type={showPwd ? "text" : "password"}
                      placeholder="Minimum 8 caractères"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      autoComplete="new-password"
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      className={`password-eye-btn${showPwd ? " password-eye-btn--active" : ""}`}
                      onClick={() => setShowPwd(p => !p)}
                      aria-label={showPwd ? "Masquer" : "Afficher"}
                    >
                      <IconEye open={showPwd} />
                    </button>
                  </div>
                </div>

                {/* confirm password */}
                <div className="signup-field">
                  <label htmlFor="signup-password-confirm">Confirmer le mot de passe</label>
                  <div className="password-input-wrapper">
                    <span className="signup-input-icon">
                      <IconLock />
                    </span>
                    <input
                      id="signup-password-confirm"
                      className="password-input signup-input-leading"
                      type={showPwd ? "text" : "password"}
                      placeholder="Retapez votre mot de passe"
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      autoComplete="new-password"
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      className={`password-eye-btn${showPwd ? " password-eye-btn--active" : ""}`}
                      onClick={() => setShowPwd(p => !p)}
                      aria-label={showPwd ? "Masquer" : "Afficher"}
                    >
                      <IconEye open={showPwd} />
                    </button>
                  </div>
                </div>
              </>
            )}

            {/* ── STEP 2: OTP ── */}
            {verificationSent && (
              <div className="signup-verify-info">
                <div className="signup-verify-msg">
                  {verifyMsg || (
                    <>
                      Nous avons envoyé un code de vérification à <strong>{email}</strong>.
                      Vérifiez également vos spams.
                    </>
                  )}
                </div>
                <div className="signup-field">
                  <label htmlFor="signup-code">Code à 6 chiffres</label>
                  <input
                    id="signup-code"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="— — — — — —"
                    value={code}
                    onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    maxLength={6}
                    className="signup-code-input"
                    autoFocus
                  />
                </div>
              </div>
            )}

            {/* error */}
            {error && (
              <div className="signup-error">
                <span>⚠</span> {error}
              </div>
            )}

            {/* submit */}
            <button type="submit" className="signup-submit" disabled={loading}>
              {loading
                ? "Chargement…"
                : verificationSent
                  ? "Confirmer et créer mon compte"
                  : "Envoyer le code de vérification"}
            </button>

            {verificationSent && (
              <button
                type="button"
                className="signup-back-btn"
                onClick={() => { setVerificationSent(false); setCode(""); setError(""); }}
              >
                ← Modifier mes informations
              </button>
            )}

          </form>

          <div className="signup-divider">Déjà membre ?</div>

          <p className="signup-footer">
            Vous avez déjà un compte ?
            <button type="button" onClick={() => navigate("/connexion")}>
              Se connecter →
            </button>
          </p>
        </div>

      </div>
    </section>
  );
}

export default CreerCompte;
