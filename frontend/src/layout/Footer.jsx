import React, { useState } from "react";
import "../css/Footer.css";
import logo from "../assets/logo.svg";

const Footer = () => {
  const [openColumn, setOpenColumn] = useState(null);

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
              <li>Accueil</li>
              <li>À propos</li>
              <li>Équipe</li>
              <li>Contact</li>
              <li>Connexion</li>
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
              <li>Mentions légales</li>
              <li>Politique de confidentialité</li>
              <li>Conditions d&apos;utilisation</li>
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
  );
};

export default Footer;