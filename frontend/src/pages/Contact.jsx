import React from "react";
import "../css/Contact.css";
import heroImage from "../assets/new-bgpages.jpg";

const IconUser = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <circle cx="12" cy="8" r="3.5" />
    <path d="M6 19c0-2.5 2.3-4.5 6-4.5s6 2 6 4.5" />
  </svg>
);

const IconMail = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <polyline points="3,7 12,13 21,7" />
  </svg>
);

const IconBuilding = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <rect x="4" y="3" width="16" height="18" rx="2" />
    <path d="M9 7h2M9 11h2M9 15h2M15 7h2M15 11h2M15 15h2" />
  </svg>
);

const IconTopic = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <path d="M4 6h16M4 12h10M4 18h7" />
  </svg>
);

const IconMessage = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
    <path d="M4 5h16a2 2 0 0 1 2 2v8.5a2 2 0 0 1-2 2H9l-5 3v-5H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" />
  </svg>
);

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
                <div className="contact-input-with-icon">
                  <span className="contact-input-icon">
                    <IconUser />
                  </span>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    className="contact-input-leading"
                    placeholder="Votre nom complet"
                    required
                  />
                </div>
              </div>
              <div className="form-field">
                <label htmlFor="email">E-mail</label>
                <div className="contact-input-with-icon">
                  <span className="contact-input-icon">
                    <IconMail />
                  </span>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    className="contact-input-leading"
                    placeholder="vous@gmail.com"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="form-row">
              <div className="form-field">
                <label htmlFor="company">Entreprise (facultatif)</label>
                <div className="contact-input-with-icon">
                  <span className="contact-input-icon">
                    <IconBuilding />
                  </span>
                  <input
                    id="company"
                    name="company"
                    type="text"
                    className="contact-input-leading"
                    placeholder="Nom de votre entreprise"
                  />
                </div>
              </div>
              <div className="form-field">
                <label htmlFor="topic">Sujet</label>
                <div className="contact-input-with-icon">
                  <span className="contact-input-icon">
                    <IconTopic />
                  </span>
                  <input
                    id="topic"
                    name="subject"
                    type="text"
                    className="contact-input-leading"
                    placeholder="Recrutement, partenariat..."
                    required
                  />
                </div>
              </div>
            </div>

            <div className="form-field form-field-full">
              <label htmlFor="message">Message</label>
              <div className="contact-input-with-icon contact-input-with-icon--textarea">
                <span className="contact-input-icon">
                  <IconMessage />
                </span>
                <textarea
                  id="message"
                  name="message"
                  rows="6"
                  className="contact-input-leading"
                  placeholder="Expliquez-nous votre besoin ou votre projet."
                  required
                />
              </div>
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