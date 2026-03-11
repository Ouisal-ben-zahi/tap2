import React, { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import "../css/Footer.css";
import logo from "../assets/logo-white.svg";
import heroBg from "../assets/hero.jpg";

const Footer = () => {
  const [openColumn, setOpenColumn] = useState(null);
  const location = useLocation();

  const navItems = [
    { label: "Accueil", path: "/" },
    { label: "À propos", path: "/a-propos" },
    { label: "Équipe", path: "/team" },
    { label: "Contact", path: "/contact" },
    { label: "Connexion", path: "/connexion" },
  ];

  const toggleColumn = (id) => {
    setOpenColumn((prev) => (prev === id ? null : id));
  };

  const openMail = (e) => {
    e.preventDefault();
    window.location.href = "mailto:tap@entrepreneursmorocco.com";
  };

  const openPhone = (e) => {
    e.preventDefault();
    window.location.href = "tel:+21277686816376";
  };

  const scrollTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <>
      {/* Section CTA au-dessus du footer (en dehors du footer) */}
      <section
        className="footer-cta"
       
      >
        <div className="footer-cta-overlay" />
        <div className="footer-cta-inner" >
          <div className="footer-cta-text">
            <p className="footer-cta-kicker">Prêts à passer à l’action ?</p>
            <h2 className="footer-cta-title">
              Transformez vos profils en{" "}
              <span className="footer-cta-accent">talents prêts à performer.</span>
            </h2>
          </div>
          <div className="footer-cta-actions">
            <a href="/apropos" className="footer-cta-btn footer-cta-btn-primary">
              Découvrir TAP
            </a>
            <a href="/contact" className="footer-cta-btn footer-cta-btn-secondary">
              Contactez-nous
            </a>
          </div>
        </div>
      </section>

      <footer className="footer-container">
        <div className="footer-inner">
          <div className="footer-brand">
            <img src={logo} alt="TAP" className="footer-logo" />
            <p className="brand-description">
              La plateforme qui transforme des profils en talents
              prêts à performer.
            </p>

            <ul className="footer-contact-list">
              <li>
                <span className="footer-contact-icon" aria-hidden>
                  @
                </span>
                <a
                  href="mailto:tap@entrepreneursmorocco.com"
                  className="footer-contact-link"
                  onClick={openMail}
                >
                  tap@entrepreneursmorocco.com
                </a>
              </li>
              <li>
                <span className="footer-contact-icon" aria-hidden>
                  ☎
                </span>
                <a
                  href="tel:+21277686816376"
                  className="footer-contact-link"
                  onClick={openPhone}
                >
                  +212 7 76 86 81 63
                </a>
              </li>
              <li>
                <span className="footer-contact-icon" aria-hidden>
                  ⬤
                </span>
                <span className="footer-contact-text">
                  Immeuble STAVROULA, Guéliz — Marrakech
                </span>
              </li>
            </ul>
          </div>

          <div className="footer-grid">
            <div
              className={`footer-column ${
                openColumn === "nav" ? "open" : ""
              }`}
            >
              <button
                type="button"
                className="footer-column-header"
                onClick={() => toggleColumn("nav")}
              >
                <h3>NAVIGATION</h3>
                <span className="footer-column-arrow" aria-hidden>
                  ▼
                </span>
              </button>
              <ul className="footer-column-content">
                {navItems.map((item) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <li
                      key={item.path}
                      className={isActive ? "footer-nav-item active" : "footer-nav-item"}
                    >
                      <Link to={item.path}>{item.label}</Link>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div
              className={`footer-column ${
                openColumn === "prod" ? "open" : ""
              }`}
            >
              <button
                type="button"
                className="footer-column-header"
                onClick={() => toggleColumn("prod")}
              >
                <h3>PRODUIT</h3>
                <span className="footer-column-arrow" aria-hidden>
                  ▼
                </span>
              </button>
              <ul className="footer-column-content">
                <li>Analyse IA du CV</li>
                <li>Score d&apos;employabilité</li>
                <li>Micro-learning</li>
                <li>Matching intelligent</li>
              </ul>
            </div>

            <div
              className={`footer-column ${
                openColumn === "legal" ? "open" : ""
              }`}
            >
              <button
                type="button"
                className="footer-column-header"
                onClick={() => toggleColumn("legal")}
              >
                <h3>LÉGAL</h3>
                <span className="footer-column-arrow" aria-hidden>
                  ▼
                </span>
              </button>
              <ul className="footer-column-content">
                <li
                  className={
                    location.pathname === "/mentions-legales"
                      ? "footer-nav-item active"
                      : "footer-nav-item"
                  }
                >
                  <Link to="/mentions-legales">Mentions légales</Link>
                </li>
                <li
                  className={
                    location.pathname === "/politique-confidentialite"
                      ? "footer-nav-item active"
                      : "footer-nav-item"
                  }
                >
                  <Link to="/politique-confidentialite">
                    Politique de confidentialité
                  </Link>
                </li>
                <li
                  className={
                    location.pathname === "/conditions-utilisation"
                      ? "footer-nav-item active"
                      : "footer-nav-item"
                  }
                >
                  <Link to="/conditions-utilisation">
                    Conditions d&apos;utilisation
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <p className="footer-bottom-left">
            © 2026 TAP — Tous droits réservés.
          </p>
          <div className="footer-bottom-right">
            <span className="footer-bottom-location">Marrakech, Maroc</span>
            <button
              type="button"
              className="footer-scroll-top"
              onClick={scrollTop}
              aria-label="Revenir en haut de la page"
            >
              ↑
            </button>
          </div>
        </div>
      </footer>
    </>
  );
};

export default Footer;