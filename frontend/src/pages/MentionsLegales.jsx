import React from "react";
import "../css/MentionsLegales.css";

const LegalArticleLink = ({ href, children }) => (
  <a href={href} className="legal-article-link" target="_blank" rel="noreferrer">
    <span className="legal-article-link-icon">↗</span>
    <span className="legal-article-link-text">{children}</span>
  </a>
);

function MentionsLegales() {
  return (
    <section className="legal-section">
      <div className="legal-inner">
        <header className="legal-header">
          <span className="legal-kicker">Légal</span>
          <h1 className="legal-title">Mentions légales — TAP</h1>
          <p className="legal-subtitle">
            Informations légales relatives au site tap-hr.com et à l&apos;exploitation de la
            plateforme TAP — Talent Acceleration Platform.
          </p>
        </header>

        <div className="legal-grid">
          {/* SOMMAIRE À GAUCHE */}
          <aside className="legal-sidebar">
            <h2 className="legal-sidebar-title">Sommaire</h2>
            <div className="legal-toc-group">
              <div className="legal-toc">
                {[
                  "Éditeur du site",
                  "Hébergement",
                  "Propriété intellectuelle",
                  "Données personnelles",
                  "Cookies",
                  "Limitation de responsabilité",
                  "Droit applicable",
                  "Contact",
                ].map((label, index) => (
                  <a
                    key={label}
                    href={`#article-${index + 1}`}
                    className="legal-toc-card"
                  >
                    <span className="legal-toc-number">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="legal-toc-label">{label}</span>
                  </a>
                ))}
              </div>
            </div>
          </aside>

          {/* CONTENU À DROITE */}
          <div className="legal-content">
            <article id="article-1" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 1 — Éditeur du site
              </h2>
              <p>
                Le site <strong>tap-hr.com</strong> est édité par <strong>TAP (Talent Acceleration Platform)</strong>,
                projet porté par <strong>Entrepreneurs Morocco</strong>.
              </p>
              <p>
                <strong>Siège social :</strong> Immeuble STAVROULA, Gueliz — Marrakech 40000, Maroc
              </p>
              <p>
                <strong>Email :</strong> tap@entrepreneursmorocco.com
                <br />
                <strong>Téléphone :</strong> +212 7 76 86 81 63
              </p>
              <p>
                <strong>Directeur de la publication :</strong> Imad El Boukhiari, Co‑Founder &amp; CEO
              </p>
            </article>

            <article id="article-2" className="legal-article-card">
              <h2 className="legal-article-heading">Article 2 — Hébergement</h2>
              <p>
                Le site est hébergé par <strong>Hostinger International Ltd.</strong>
              </p>
              <p>
                <strong>Adresse :</strong> 61 Lordou Vironos Street, 6023 Larnaca, Chypre
                <br />
                <strong>Site :</strong>{" "}
                <LegalArticleLink href="https://www.hostinger.com">
                  hostinger.com
                </LegalArticleLink>
              </p>
            </article>

            <article id="article-3" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 3 — Propriété intellectuelle
              </h2>
              <p>
                L&apos;ensemble du contenu du site <strong>tap-hr.com</strong> (textes, images, logos,
                graphismes, icônes, vidéos, sons, logiciels, bases de données, etc.) est
                protégé par le droit de la propriété intellectuelle.
              </p>
              <p>
                Toute reproduction, représentation, modification, distribution ou
                exploitation, totale ou partielle, du contenu de ce site, par quelque
                procédé que ce soit, sans l&apos;autorisation préalable et écrite de TAP,
                est strictement interdite et constitue une contrefaçon sanctionnée par la loi.
              </p>
              <p>
                Les marques, logos et noms de domaine figurant sur ce site sont la
                propriété exclusive de TAP ou de ses partenaires.
              </p>
            </article>

            <article id="article-4" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 4 — Données personnelles
              </h2>
              <p>
                Les informations recueillies via le formulaire de contact sont destinées à
                TAP et servent uniquement à traiter votre demande.
              </p>
              <p>
                Conformément à la loi marocaine n° 09-08 relative à la protection des
                personnes physiques à l&apos;égard du traitement des données à caractère
                personnel, vous disposez d&apos;un droit d&apos;accès, de rectification et
                de suppression de vos données.
              </p>
              <p>
                Pour exercer ces droits, contactez‑nous à :{" "}
                <strong>tap@entrepreneursmorocco.com</strong>.
              </p>
            </article>

            <article id="article-5" className="legal-article-card">
              <h2 className="legal-article-heading">Article 5 — Cookies</h2>
              <p>
                Le site <strong>tap-hr.com</strong> peut utiliser des cookies à des fins de
                mesure d&apos;audience et d&apos;amélioration de l&apos;expérience
                utilisateur.
              </p>
              <p>
                Vous pouvez configurer votre navigateur pour refuser les cookies. Toutefois,
                certaines fonctionnalités du site pourraient ne plus être accessibles.
              </p>
            </article>

            <article id="article-6" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 6 — Limitation de responsabilité
              </h2>
              <p>
                TAP s&apos;efforce de fournir des informations aussi précises que possible
                sur le site. Toutefois, TAP ne pourra être tenue responsable des omissions,
                inexactitudes ou des carences dans la mise à jour de ces informations.
              </p>
              <p>
                TAP décline toute responsabilité en cas d&apos;interruption du site, de
                bugs, d&apos;incompatibilité ou de dommages résultant de l&apos;utilisation
                du site.
              </p>
            </article>

            <article id="article-7" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 7 — Droit applicable
              </h2>
              <p>
                Les présentes mentions légales sont régies par le droit marocain. En cas de
                litige, les tribunaux de Marrakech seront seuls compétents.
              </p>
            </article>

            <article id="article-8" className="legal-article-card">
              <h2 className="legal-article-heading">Article 8 — Contact</h2>
              <p>
                Pour toute question relative aux présentes mentions légales :
              </p>
              <p>
                <strong>TAP — Entrepreneurs Morocco</strong>
                <br />
                Immeuble STAVROULA, Gueliz — Marrakech 40000, Maroc
              </p>
              <p>
                <strong>Email :</strong>{" "}
                <LegalArticleLink href="mailto:tap@entrepreneursmorocco.com">
                  tap@entrepreneursmorocco.com
                </LegalArticleLink>
                <br />
                <strong>Téléphone :</strong>{" "}
                <LegalArticleLink href="tel:+21277686816376">
                  +212 7 76 86 81 63
                </LegalArticleLink>
              </p>
              <p className="legal-footer-note">
                Dernière mise à jour : <strong>Mars 2026</strong>
              </p>
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}

export default MentionsLegales;

