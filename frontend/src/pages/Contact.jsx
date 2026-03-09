import React from "react";
import "../css/Contact.css";
import heroImage from "../assets/new-bgpages.jpg";

function Contact() {
  return (
    <section
      className="contact-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="contact-inner">
        <header className="contact-header">
          <div className="contact-badge">Contact</div>
          <h1 className="contact-title">
            Contactez<span className="contact-title-accent">-nous</span>
          </h1>
          <p className="contact-subtitle">
            Une question ou un besoin ? Nous revenons vers vous rapidement.
          </p>
        </header>

        <div className="contact-grid">
          <div className="contact-info-column">
            <div className="contact-info-card contact-info-card--primary">
              <div className="contact-info-icon">
                <span className="contact-info-icon-symbol" aria-hidden="true">
                  ✉
                </span>
              </div>
              <div className="contact-info-text">
                <div className="contact-info-label">Email</div>
                <div className="contact-info-value">
                  tap@entreprenupmaroc.com
                </div>
              </div>
            </div>

            <div className="contact-info-card">
              <div className="contact-info-icon">
                <span className="contact-info-icon-symbol" aria-hidden="true">
                  ☎
                </span>
              </div>
              <div className="contact-info-text">
                <div className="contact-info-label">Téléphone</div>
                <div className="contact-info-value">+212 7 76 88 81 63</div>
              </div>
            </div>

            <div className="contact-info-card">
              <div className="contact-info-icon">
                <span className="contact-info-icon-symbol" aria-hidden="true">
                  ⌂
                </span>
              </div>
              <div className="contact-info-text">
                <div className="contact-info-label">Adresse</div>
                <div className="contact-info-value">
                  Immeuble STAMOULA, Guéliz – Marrakech
                </div>
              </div>
            </div>
          </div>

          <form
            className="contact-form"
            method="POST"
            action="https://formsubmit.co/ouissalbenzahi@gmail.com"
          >
            <input type="hidden" name="_captcha" value="false" />
            <input
              type="hidden"
              name="_subject"
              value="Nouveau message depuis le site TAP"
            />

            <div className="form-row">
              <div className="form-field">
                <label htmlFor="name">Nom et prénom</label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  placeholder="Votre nom complet"
                  required
                />
              </div>
              <div className="form-field">
                <label htmlFor="email">E-mail</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="vous@gmail.com"
                  required
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-field">
                <label htmlFor="company">Entreprise (facultatif)</label>
                <input
                  id="company"
                  name="company"
                  type="text"
                  placeholder="Nom de votre entreprise"
                />
              </div>
              <div className="form-field">
                <label htmlFor="topic">Sujet</label>
                <input
                  id="topic"
                  name="subject"
                  type="text"
                  placeholder="Recrutement, partenariat..."
                  required
                />
              </div>
            </div>

            <div className="form-field form-field-full">
              <label htmlFor="message">Message</label>
              <textarea
                id="message"
                name="message"
                rows="6"
                placeholder="Expliquez-nous votre besoin ou votre projet."
                required
              />
            </div>

            <div className="contact-submit-wrapper">
              <button type="submit" className="contact-submit">
                ENVOYER LE MESSAGE
              </button>
            </div>
          </form>
        </div>

        <section className="contact-cta">
          <div className="contact-cta-label">COMMENCEZ MAINTENANT</div>
          <h2 className="contact-cta-title">
            Prêt à recruter <span className="contact-cta-title-accent">autrement&nbsp;?</span>
          </h2>
          <p className="contact-cta-subtitle">
            Rejoignez les entreprises qui recrutent des talents préparés par l&apos;IA.
          </p>
          <div className="contact-cta-actions">
            <a
              href="https://demo.tap-hr.com/login"
              className="contact-cta-btn contact-cta-btn-primary"
            >
              ACCÉDER À LA PLATEFORME &rarr;
            </a>
          </div>
        </section>
      </div>
    </section>
  );
}

export default Contact;