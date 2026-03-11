import React from "react";
import "../css/ConditionsUtilisation.css";

const LegalArticleLink = ({ href, children }) => (
  <a href={href} className="legal-article-link" target="_blank" rel="noreferrer">
    <span className="legal-article-link-icon">↗</span>
    <span className="legal-article-link-text">{children}</span>
  </a>
);

function ConditionsUtilisation() {
  const tocItems = [
    "Objet",
    "Description des services",
    "Inscription et compte utilisateur",
    "Utilisation acceptable",
    "Propriété intellectuelle",
    "Contenu utilisateur",
    "Limitation de responsabilité",
    "Protection des données",
    "Modification des CGU",
    "Résiliation",
    "Droit applicable et juridiction",
    "Contact",
  ];

  return (
    <section className="legal-section">
      <div className="legal-inner">
        <header className="legal-header">
          <span className="legal-kicker">Conditions d&apos;utilisation</span>
          <h1 className="legal-title">Conditions générales d&apos;utilisation</h1>
          <p className="legal-subtitle">
            Les règles qui régissent l&apos;utilisation du site tap-hr.com et de la
            plateforme TAP — Talent Acceleration Platform.
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
              <h2 className="legal-article-heading">Article 1 — Objet</h2>
              <p>
                Les présentes conditions générales d&apos;utilisation (CGU) régissent
                l&apos;accès et l&apos;utilisation du site <strong>tap-hr.com</strong> et
                de la plateforme TAP (Talent Acceleration Platform).
              </p>
              <p>
                En accédant au site ou en utilisant la plateforme, vous acceptez sans
                réserve les présentes CGU. Si vous n&apos;acceptez pas ces conditions,
                veuillez ne pas utiliser le site.
              </p>
            </article>

            <article id="article-2" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 2 — Description des services
              </h2>
              <p>
                TAP est une plateforme d&apos;employabilité assistée par l&apos;intelligence
                artificielle qui propose les services suivants :
              </p>
              <ul className="legal-list">
                <li>
                  <strong>Analyse de CV par IA :</strong> évaluation automatisée des
                  compétences et du profil.
                </li>
                <li>
                  <strong>Score d&apos;employabilité :</strong> notation objective basée sur
                  les critères du marché.
                </li>
                <li>
                  <strong>Micro-learning :</strong> parcours de formation personnalisés pour
                  renforcer les compétences.
                </li>
                <li>
                  <strong>Matching intelligent :</strong> mise en relation entre candidats et
                  entreprises partenaires.
                </li>
              </ul>
              <p>
                TAP se réserve le droit de modifier, suspendre ou interrompre tout ou partie
                de ses services à tout moment, avec ou sans préavis.
              </p>
            </article>

            <article id="article-3" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 3 — Inscription et compte utilisateur
              </h2>
              <p>
                L&apos;accès à certaines fonctionnalités de la plateforme peut nécessiter la
                création d&apos;un compte utilisateur.
              </p>
              <p>L&apos;utilisateur s&apos;engage à :</p>
              <ul className="legal-list">
                <li>Fournir des informations exactes, complètes et à jour.</li>
                <li>Maintenir la confidentialité de ses identifiants de connexion.</li>
                <li>
                  Ne pas créer de compte avec une fausse identité ou au nom d&apos;un tiers
                  sans autorisation.
                </li>
                <li>
                  Informer immédiatement TAP en cas d&apos;utilisation non autorisée de son
                  compte.
                </li>
              </ul>
              <p>
                TAP se réserve le droit de suspendre ou supprimer tout compte en cas de
                violation des présentes CGU.
              </p>
            </article>

            <article id="article-4" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 4 — Utilisation acceptable
              </h2>
              <p>
                L&apos;utilisateur s&apos;engage à utiliser le site et la plateforme de
                manière licite et conforme aux présentes CGU. Il est notamment interdit de :
              </p>
              <ul className="legal-list">
                <li>Soumettre des informations fausses, trompeuses ou frauduleuses.</li>
                <li>Utiliser la plateforme à des fins illégales ou non autorisées.</li>
                <li>Tenter de contourner les mesures de sécurité du site.</li>
                <li>
                  Collecter des données personnelles d&apos;autres utilisateurs sans leur
                  consentement.
                </li>
                <li>
                  Utiliser des systèmes automatisés (robots, scrapers) pour accéder au site.
                </li>
                <li>Porter atteinte au fonctionnement normal de la plateforme.</li>
              </ul>
            </article>

            <article id="article-5" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 5 — Propriété intellectuelle
              </h2>
              <p>
                L&apos;ensemble des éléments du site et de la plateforme (design, textes,
                logos, algorithmes, bases de données, code source) sont protégés par le
                droit de la propriété intellectuelle et restent la propriété exclusive de
                TAP.
              </p>
              <p>
                L&apos;utilisateur bénéficie d&apos;un droit d&apos;utilisation personnel et
                non transférable du site et de la plateforme dans le cadre des services
                proposés.
              </p>
              <p>
                Toute reproduction, copie ou utilisation non autorisée du contenu est
                strictement interdite.
              </p>
            </article>

            <article id="article-6" className="legal-article-card">
              <h2 className="legal-article-heading">Article 6 — Contenu utilisateur</h2>
              <p>
                En soumettant du contenu sur la plateforme (CV, informations de profil,
                etc.), l&apos;utilisateur accorde à TAP une licence non exclusive pour
                traiter, analyser et utiliser ces données dans le cadre des services
                proposés.
              </p>
              <p>
                L&apos;utilisateur garantit qu&apos;il dispose de tous les droits nécessaires
                sur le contenu qu&apos;il soumet et que celui-ci ne porte atteinte aux
                droits d&apos;aucun tiers.
              </p>
            </article>

            <article id="article-7" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 7 — Limitation de responsabilité
              </h2>
              <p>
                TAP fournit ses services « en l&apos;état ». TAP ne garantit pas que les
                services seront ininterrompus, sécurisés ou exempts d&apos;erreurs.
              </p>
              <p>TAP ne saurait être tenue responsable :</p>
              <ul className="legal-list">
                <li>
                  Des décisions prises sur la base des scores ou analyses fournis par
                  l&apos;IA.
                </li>
                <li>
                  Des résultats des processus de recrutement entre candidats et entreprises.
                </li>
                <li>
                  Des dommages indirects, pertes de données ou de profits liés à
                  l&apos;utilisation du site.
                </li>
                <li>
                  De l&apos;indisponibilité temporaire du site pour maintenance ou mise à
                  jour.
                </li>
              </ul>
              <p>
                Les scores d&apos;employabilité et analyses IA sont fournis à titre
                indicatif et ne constituent pas des garanties d&apos;embauche.
              </p>
            </article>

            <article id="article-8" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 8 — Protection des données
              </h2>
              <p>
                TAP s&apos;engage à protéger les données personnelles de ses utilisateurs
                conformément à sa Politique de confidentialité et à la loi marocaine n°
                09-08.
              </p>
              <p>
                Pour plus d&apos;informations, consultez notre{" "}
                <LegalArticleLink href="/politique-confidentialite">
                  Politique de confidentialité
                </LegalArticleLink>
                .
              </p>
            </article>

            <article id="article-9" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 9 — Modification des CGU
              </h2>
              <p>
                TAP se réserve le droit de modifier les présentes CGU à tout moment. Les
                modifications prennent effet dès leur publication sur le site.
              </p>
              <p>
                L&apos;utilisation continue du site après modification constitue une
                acceptation des nouvelles conditions.
              </p>
              <p>
                Nous vous encourageons à consulter régulièrement cette page pour rester
                informé des éventuelles mises à jour.
              </p>
            </article>

            <article id="article-10" className="legal-article-card">
              <h2 className="legal-article-heading">Article 10 — Résiliation</h2>
              <p>
                L&apos;utilisateur peut cesser d&apos;utiliser le site à tout moment et
                demander la suppression de son compte en contactant TAP.
              </p>
              <p>
                TAP se réserve le droit de résilier ou suspendre l&apos;accès de tout
                utilisateur qui enfreint les présentes CGU, sans préavis ni indemnité.
              </p>
            </article>

            <article id="article-11" className="legal-article-card">
              <h2 className="legal-article-heading">
                Article 11 — Droit applicable et juridiction
              </h2>
              <p>
                Les présentes CGU sont régies par le droit marocain. En cas de litige
                relatif à l&apos;interprétation ou à l&apos;exécution des présentes
                conditions, les parties s&apos;efforceront de résoudre le différend à
                l&apos;amiable.
              </p>
              <p>
                À défaut d&apos;accord amiable, les tribunaux compétents de Marrakech
                seront seuls habilités à connaître du litige.
              </p>
            </article>

            <article id="article-12" className="legal-article-card">
              <h2 className="legal-article-heading">Article 12 — Contact</h2>
              <p>Pour toute question relative aux présentes CGU :</p>
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

export default ConditionsUtilisation;

