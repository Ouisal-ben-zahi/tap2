import React from "react";
import "../css/PolitiqueConfidentialite.css";

const LegalArticleLink = ({ href, children }) => (
  <a href={href} className="legal-article-link" target="_blank" rel="noreferrer">
    <span className="legal-article-link-icon">↗</span>
    <span className="legal-article-link-text">{children}</span>
  </a>
);

function PolitiqueConfidentialite() {
  const tocItems = [
    "Introduction",
    "Données collectées",
    "Finalités du traitement",
    "Base légale du traitement",
    "Durée de conservation",
    "Partage des données",
    "Sécurité des données",
    "Vos droits",
    "Cookies",
    "Modifications",
    "Contact",
  ];

  return (
    <section className="legal-section">
      <div className="legal-inner">
        <header className="legal-header">
          <span className="legal-kicker">Confidentialité</span>
          <h1 className="legal-title">Politique de confidentialité</h1>
          <p className="legal-subtitle">
            Comment nous collectons, utilisons et protégeons vos données personnelles
            lorsque vous utilisez le site tap-hr.com et la plateforme TAP.
          </p>
        </header>

        <div className="legal-grid">
          {/* SOMMAIRE GAUCHE */}
          <aside className="legal-sidebar">
            <h2 className="legal-sidebar-title">Sommaire</h2>
            <div className="legal-toc-group">
              <div className="legal-toc">
                {tocItems.map((label, index) => (
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

          {/* CONTENU DROITE */}
          <div className="legal-content">
            <article id="article-1" className="legal-article-card">
              <h2 className="legal-article-heading">Article 1 — Introduction</h2>
              <p>
                TAP (Talent Acceleration Platform) accorde une importance fondamentale à
                la protection de vos données personnelles. La présente politique de
                confidentialité décrit les données que nous collectons, les raisons de
                cette collecte et la manière dont nous les utilisons.
              </p>
              <p>
                En utilisant le site <strong>tap-hr.com</strong> et la plateforme TAP,
                vous acceptez les pratiques décrites dans cette politique.
              </p>
            </article>

            <article id="article-2" className="legal-article-card">
              <h2 className="legal-article-heading">Article 2 — Données collectées</h2>
              <p>Nous collectons les données suivantes :</p>
              <ul className="legal-list">
                <li>
                  <strong>Données d&apos;identification :</strong> nom, prénom, adresse
                  e‑mail, numéro de téléphone.
                </li>
                <li>
                  <strong>Données professionnelles :</strong> CV, parcours académique,
                  compétences, expériences professionnelles.
                </li>
                <li>
                  <strong>Données de navigation :</strong> adresse IP, type de
                  navigateur, pages consultées, durée de visite.
                </li>
                <li>
                  <strong>Données de formulaire :</strong> toute information transmise via
                  le formulaire de contact.
                </li>
              </ul>
            </article>

            <article id="article-3" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 3 — Finalités du traitement
              </h2>
              <p>
                Vos données personnelles sont collectées et traitées pour les finalités
                suivantes :
              </p>
              <ul className="legal-list">
                <li>
                  Analyse de CV et génération du score d&apos;employabilité via notre IA.
                </li>
                <li>Personnalisation des parcours de micro‑learning.</li>
                <li>Matching intelligent entre candidats et entreprises.</li>
                <li>Réponse à vos demandes via le formulaire de contact.</li>
                <li>
                  Amélioration continue de nos services et de l&apos;expérience
                  utilisateur.
                </li>
                <li>Statistiques et analyses d&apos;audience anonymisées.</li>
              </ul>
            </article>

            <article id="article-4" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 4 — Base légale du traitement
              </h2>
              <p>Le traitement de vos données repose sur :</p>
              <ul className="legal-list">
                <li>Votre consentement explicite lors de l&apos;utilisation de la plateforme.</li>
                <li>L&apos;exécution d&apos;un contrat ou de mesures précontractuelles.</li>
                <li>
                  L&apos;intérêt légitime de TAP pour améliorer ses services et assurer le
                  bon fonctionnement de la plateforme.
                </li>
              </ul>
              <p>
                Le traitement est conforme à la loi marocaine n° 09‑08 relative à la
                protection des personnes physiques à l&apos;égard du traitement des
                données à caractère personnel.
              </p>
            </article>

            <article id="article-5" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 5 — Durée de conservation
              </h2>
              <p>
                Vos données personnelles sont conservées pendant la durée nécessaire aux
                finalités pour lesquelles elles ont été collectées :
              </p>
              <ul className="legal-list">
                <li>Données de profil candidat : 24 mois après la dernière activité.</li>
                <li>Données de contact (formulaire) : 12 mois.</li>
                <li>Données de navigation : 13 mois.</li>
              </ul>
              <p>
                Au‑delà de ces durées, vos données sont supprimées ou anonymisées.
              </p>
            </article>

            <article id="article-6" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 6 — Partage des données
              </h2>
              <p>TAP ne vend jamais vos données personnelles à des tiers.</p>
              <p>Vos données peuvent être partagées uniquement dans les cas suivants :</p>
              <ul className="legal-list">
                <li>
                  Avec les entreprises partenaires, dans le cadre du matching
                  candidat‑entreprise, et uniquement avec votre consentement.
                </li>
                <li>
                  Avec nos sous‑traitants techniques (hébergement, analyse IA) qui sont
                  contractuellement tenus de protéger vos données.
                </li>
                <li>En cas d&apos;obligation légale ou de décision judiciaire.</li>
              </ul>
            </article>

            <article id="article-7" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 7 — Sécurité des données
              </h2>
              <p>
                TAP met en œuvre des mesures techniques et organisationnelles appropriées
                pour protéger vos données :
              </p>
              <ul className="legal-list">
                <li>Chiffrement des données en transit (HTTPS/TLS).</li>
                <li>Accès restreint aux données personnelles.</li>
                <li>Sauvegardes régulières et sécurisées.</li>
                <li>Surveillance continue des systèmes.</li>
              </ul>
            </article>

            <article id="article-8" className="legal-article-card">
              <h2 className="legal-article-heading">Article 8 — Vos droits</h2>
              <p>
                Conformément à la loi marocaine n° 09‑08, vous disposez des droits
                suivants :
              </p>
              <ul className="legal-list">
                <li>
                  <strong>Droit d&apos;accès :</strong> obtenir la confirmation du
                  traitement de vos données et en obtenir une copie.
                </li>
                <li>
                  <strong>Droit de rectification :</strong> corriger vos données
                  inexactes ou incomplètes.
                </li>
                <li>
                  <strong>Droit de suppression :</strong> demander l&apos;effacement de
                  vos données.
                </li>
                <li>
                  <strong>Droit d&apos;opposition :</strong> vous opposer au traitement de
                  vos données.
                </li>
                <li>
                  <strong>Droit à la portabilité :</strong> recevoir vos données dans un
                  format structuré.
                </li>
              </ul>
              <p>
                Pour exercer ces droits, contactez‑nous à :{" "}
                <LegalArticleLink href="mailto:tap@entrepreneursmorocco.com">
                  tap@entrepreneursmorocco.com
                </LegalArticleLink>
                .
              </p>
            </article>

            <article id="article-9" className="legal-article-card">
              <h2 className="legal-article-heading">Article 9 — Cookies</h2>
              <p>
                Notre site utilise des cookies essentiels au fonctionnement du site et des
                cookies analytiques pour mesurer l&apos;audience.
              </p>
              <p>
                Vous pouvez à tout moment configurer votre navigateur pour accepter ou
                refuser les cookies. Le refus de certains cookies peut limiter votre accès
                à certaines fonctionnalités.
              </p>
            </article>

            <article id="article-10" className="legal-article-card">
              <h2 className="legal-article-heading">Article 10 — Modifications</h2>
              <p>
                TAP se réserve le droit de modifier cette politique de confidentialité à
                tout moment. Les modifications prennent effet dès leur publication sur le
                site.
              </p>
              <p>
                Nous vous encourageons à consulter régulièrement cette page afin de rester
                informé des éventuelles mises à jour.
              </p>
            </article>

            <article id="article-11" className="legal-article-card">
              <h2 className="legal-article-heading">Article 11 — Contact</h2>
              <p>
                Pour toute question relative à cette politique de confidentialité ou à vos
                données personnelles :
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
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}

export default PolitiqueConfidentialite;

