import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../css/Contact.css";
import heroImage from "../assets/new-bgpages.jpg";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:3000";

function Connexion() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!email.trim() || !password.trim()) {
      setError("Email et mot de passe sont obligatoires.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
        credentials: "include",
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setError(data.message || "Identifiants incorrects.");
        return;
      }

      const userRole = data.role || data.user?.role;
      const userEmail = data.email || data.user?.email || email.trim();
      const userId = data.id || data.user?.id;

      if (data.token) {
        sessionStorage.setItem("authToken", data.token);
      }
      if (userRole) {
        sessionStorage.setItem("profileType", userRole);
      }
      if (userEmail) {
        sessionStorage.setItem("userEmail", userEmail);
      }
      if (userId) {
        sessionStorage.setItem("userId", String(userId));
      }

      const targetRoute =
        userRole === "recruteur" ? "/dashboard-recruteur" : "/dashboard-candidat";

      navigate(targetRoute);
    } catch (err) {
      setError("Erreur de connexion au serveur.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="contact-section connexion-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="contact-inner">
        <header className="contact-header">
          <div className="contact-badge">Connexion</div>
          <h1 className="contact-title">Se connecter</h1>
          <p className="contact-subtitle">Accédez à votre espace TAP.</p>
        </header>

        <div className="contact-grid">
          <form className="contact-form" onSubmit={handleSubmit}>
            <div className="form-field form-field-full">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                name="email"
                placeholder="vous@exemple.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-field form-field-full">
              <label htmlFor="login-password">Mot de passe</label>
              <div className="password-input-wrapper">
                <input
                  id="login-password"
                  className="password-input"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  placeholder="Votre mot de passe"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className={
                    "password-eye" + (showPassword ? " password-eye--active" : "")
                  }
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={
                    showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"
                  }
                />
              </div>
            </div>

            {error && (
              <div
                className="form-field form-field-full"
                style={{ color: "#f97373" }}
              >
                {error}
              </div>
            )}

            <div className="contact-submit-wrapper">
              <button
                type="submit"
                className="contact-submit"
                disabled={loading}
              >
                {loading ? "Connexion..." : "SE CONNECTER"}
              </button>
            </div>

            <div
              className="form-field form-field-full"
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "13px",
                color: "#9ca3af",
                marginTop: "6px",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  // TODO: implémenter la navigation vers page de réinitialisation
                }}
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  color: "#9ca3af",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Mot de passe oublié ?
              </button>
              <button
                type="button"
                className="login-create-account-link"
                onClick={() => navigate("/creer-compte")}
              >
                Créer un compte
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}

export default Connexion;


