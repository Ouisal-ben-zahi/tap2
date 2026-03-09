import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../css/Contact.css";
import heroImage from "../assets/new-bgpages.jpg";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

function CreerCompte() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [suggestedPassword, setSuggestedPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [verificationSent, setVerificationSent] = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");
  const [verificationMessage, setVerificationMessage] = useState("");
  const [code, setCode] = useState("");

  const generateSecurePassword = () => {
    const length = 14;
    const chars =
      "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}";
    let result = "";
    for (let i = 0; i < length; i += 1) {
      const index = Math.floor(Math.random() * chars.length);
      result += chars[index];
    }
    setSuggestedPassword(result);
  };

  return (
    <section
      className="contact-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="contact-inner">
        <header className="contact-header">
          <div className="contact-heading">
            <div className="contact-heading-main">CRÉER UN COMPTE</div>
          </div>
        </header>

        <div className="contact-grid">
          <form
            className="contact-form"
            onSubmit={async (e) => {
              e.preventDefault();
              setError("");
              const form = e.target;
              const email = form.email?.value?.trim();
              const pwd = form.password?.value;
              const role = form.accountType?.value;

              if (verificationSent) {
                if (!pendingEmail || !code.trim()) return;
                setLoading(true);
                try {
                  const res = await fetch(`${API_BASE}/auth/verify-and-register`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email: pendingEmail || email, code: code.trim() }),
                  });
                  const data = await res.json().catch(() => ({}));
                  if (!res.ok) {
                    setError(data.message || "Code invalide ou expiré.");
                    return;
                  }
                  sessionStorage.setItem("profileType", data.role);
                  sessionStorage.setItem("userEmail", data.email);
                  navigate("/connexion", { replace: true });
                } catch (err) {
                  setError("Erreur de connexion au serveur");
                } finally {
                  setLoading(false);
                }
                return;
              }

              if (!email || !pwd || !role) return;
              setLoading(true);
              try {
                const res = await fetch(`${API_BASE}/auth/send-verification`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ email, password: pwd, role }),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                  setError(data.message || "Erreur lors de l'envoi du code.");
                  return;
                }
                setPendingEmail(email);
                setVerificationMessage(data.message || "");
                setVerificationSent(true);
              } catch (err) {
                setError("Erreur de connexion au serveur");
              } finally {
                setLoading(false);
              }
            }}
          >
            {verificationSent && (
              <div className="form-field form-field-full verification-info">
                <p className="verification-message">{verificationMessage}</p>
                <label htmlFor="signup-code">Code reçu par email</label>
                <input
                  id="signup-code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  maxLength={6}
                  className="code-input"
                />
              </div>
            )}

            {!verificationSent && (
              <>
            <div className="form-field form-field-full account-type-field">
              <span className="account-type-label">Type de compte</span>
              <div className="account-type-radios">
                <label className="account-type-radio">
                  <input
                    type="radio"
                    name="accountType"
                    value="candidat"
                    defaultChecked
                  />
                  <span>Candidat</span>
                </label>
                <label className="account-type-radio">
                  <input
                    type="radio"
                    name="accountType"
                    value="recruteur"
                  />
                  <span>Recruteur</span>
                </label>
              </div>
            </div>

            <div className="form-field form-field-full">
              <label htmlFor="signup-email">Email</label>
              <input
                id="signup-email"
                type="email"
                name="email"
                placeholder="vous@exemple.com"
                defaultValue={pendingEmail}
                required
                readOnly={verificationSent}
              />
            </div>

            <div className="form-field form-field-full">
              <label htmlFor="signup-password">Mot de passe</label>
              <div className="password-input-row">
                <div className="password-input-wrapper">
                  <input
                    id="signup-password"
                    className="password-input"
                    type={showPassword ? "text" : "password"}
                    name="password"
                    placeholder="Votre mot de passe"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => {
                      setShowGenerate(true);
                      if (!suggestedPassword) {
                        generateSecurePassword();
                      }
                    }}
                    required
                    minLength={8}
                  />
                  <button
                    type="button"
                    className={
                      "password-eye" + (showPassword ? " password-eye--active" : "")
                    }
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  />
                </div>
              </div>
              {showGenerate && suggestedPassword && (
                <div className="password-suggest-below">
                  <button
                    type="button"
                    className="password-suggest-link"
                    onClick={() => setPassword(suggestedPassword)}
                  >
                    Utiliser ce mot de passe sécurisé :{" "}
                    <span className="password-suggest-value">{suggestedPassword}</span>
                  </button>
                </div>
              )}
            </div>
            </>
            )}

            {error && (
              <div className="form-field form-field-full" style={{ color: "#c00" }}>
                {error}
              </div>
            )}

            <div className="contact-submit-wrapper">
              <button type="submit" className="contact-submit" disabled={loading}>
                {loading
                  ? "Envoi…"
                  : verificationSent
                    ? "Vérifier et créer mon compte"
                    : "Envoyer le code de vérification"}
              </button>
              {verificationSent && (
                <button
                  type="button"
                  className="contact-submit-back"
                  onClick={() => {
                    setVerificationSent(false);
                    setCode("");
                    setError("");
                  }}
                >
                  Modifier l’email ou le mot de passe
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}

export default CreerCompte;

