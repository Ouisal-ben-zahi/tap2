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

  return (
    <footer className="footer-container">
      <div className="footer-inner">
        {/* Logo aligné en haut */}
        <div className="footer-brand">
          <img src={logo} alt="TAP" className="footer-logo" />
          <p className="brand-description">
            PLATEFORME D'EMPLOYABILITÉ ASSISTÉE
            PAR INTELLIGENCE ARTIFICIELLE.
          </p>
        </div>

        <div className="footer-divider"></div>

        <div className="footer-grid">
          <div className={`footer-column ${openColumn === "nav" ? "open" : ""}`}>
            <button type="button" className="footer-column-header" onClick={() => toggleColumn("nav")}>
              <h3>NAVIGATION</h3>
              <span className="footer-column-arrow" aria-hidden>▼</span>
            </button>
            <ul className="footer-column-content">
              <li>Accueil</li>
              <li>Comment ça marche</li>
              <li>À propos</li>
              <li>Ressources</li>
              <li>Connexion</li>
              <li>Créer mon profil</li>
            </ul>
          </div>

          <div className={`footer-column ${openColumn === "prod" ? "open" : ""}`}>
            <button type="button" className="footer-column-header" onClick={() => toggleColumn("prod")}>
              <h3>PRODUIT</h3>
              <span className="footer-column-arrow" aria-hidden>▼</span>
            </button>
            <ul className="footer-column-content">
              <li>Analyse IA du CV</li>
              <li>Score d'employabilité</li>
              <li>Micro-learning</li>
              <li>Portfolio généré</li>
            </ul>
          </div>

          <div className={`footer-column ${openColumn === "legal" ? "open" : ""}`}>
            <button type="button" className="footer-column-header" onClick={() => toggleColumn("legal")}>
              <h3>LÉGAL</h3>
              <span className="footer-column-arrow" aria-hidden>▼</span>
            </button>
            <ul className="footer-column-content">
              <li>Mentions légales</li>
              <li>Politique de confidentialité</li>
              <li>Conditions d'utilisation</li>
              <li>Gestion des données</li>
            </ul>
          </div>

          <div className={`footer-column contact-column ${openColumn === "contact" ? "open" : ""}`}>
            <button type="button" className="footer-column-header" onClick={() => toggleColumn("contact")}>
              <h3>CONTACT</h3>
              <span className="footer-column-arrow" aria-hidden>▼</span>
            </button>
            <div className="footer-column-content">
              <div className="contact-block">
                <strong>Email</strong>
                <a href="mailto:tap@entrepreneursmorocco.com" className="contact-link" onClick={openMail}>tap@entrepreneursmorocco.com</a>
              </div>
              <div className="contact-block">
                <strong>Téléphone</strong>
                <a href="tel:+21277686816376" className="contact-link" onClick={openPhone}>+212 776 86 81 63 76</a>
              </div>
              <div className="contact-block">
                <strong>Adresse</strong>
                <a
                  href="https://www.google.com/maps/search/?api=1&query=Immeuble+STAVROULA+gueliz+route+Av+4ème+D.M.M.+Marrakesh+4000"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="contact-link"
                >
                  à Camp militaire, Immeuble STAVROULA , gueliz route de, Av. 4ème D.M.M., Marrakesh 4000
                </a>
              </div>
              
            </div>
          </div>
        </div>
      </div>

      <div className="footer-copyright">
        <p>© 2026 TAP — TOUS DROITS RÉSERVÉS.</p>
      </div>
    </footer>
  );
};

export default Footer;