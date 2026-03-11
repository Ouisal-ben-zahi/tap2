import React from "react";
import "../css/Team.css";
import heroImage from "../assets/new-bgpages.jpg";
import imadAvatar from "../assets/imad-el-boukhiari.png";
import zakariaAvatar from "../assets/zakaria-Ajmil.png";
import hajarAvatar from "../assets/Hajar-el-aouni.jpg";
import jawharAvatar from "../assets/Juwher Profil.jpg";
import ouissalAvatar from "../assets/Ouissal-ben-zahi.jpg";

const founders = [
  {
    name: "Imad El Boukhiari",
    role: "Co‑Founder & CEO",
    avatar: imadAvatar,
    linkedinUrl:
      "https://communik-agence.slack.com/archives/D0964BMSFDX/p1772538933409959",
    focusItems: [
      "Expert en IA (LLM) & systèmes intelligents",
      "Spécialiste blockchain & finance décentralisée",
      "Conception scoring & matching intelligent",
      "Vision produit & stratégie technologique TAP",
    ],
  },
  {
    name: "Zakaria Ajmil",
    role: "Co‑Founder & COO",
    avatar: zakariaAvatar,
    linkedinUrl:
      "https://communik-agence.slack.com/archives/D0964BMSFDX/p1772538949427899",
    focusItems: [
      "Professeur d’économie",
      "Expert en marketing & communication stratégique",
      "Structuration acquisition & activation marché",
      "Déploiement partenariats universités & entreprises",
    ],
  },
];

const teamMembers = [
  {
    name: "Hajar El Aouni",
    role: "AI Product Lead",
    avatar: hajarAvatar,
    linkedinUrl:
      "https://communik-agence.slack.com/archives/D09SH22HYJC/p1772538959242339",
    focusItems: [
      "Intégration modèles IA & LLM",
      "Optimisation scoring & matching",
      "Structuration logique produit IA",
      "Amélioration continue des performances",
    ],
  },
  {
    name: "Ouissal Ben Zahi",
    role: "Lead Full‑Stack Developer",
    avatar: ouissalAvatar,
    linkedinUrl: "https://www.linkedin.com/in/ouissal-ben-zahi/",
    focusItems: [
      "Architecture backend & API",
      "Déploiement cloud & scalabilité",
      "Sécurisation & gestion des données",
      "Intégration IA côté infrastructure",
    ],
  },
  {
    name: "Juwher",
    role: "Product Designer (UI/UX)",
    avatar: jawharAvatar,
    linkedinUrl:
      "https://communik-agence.slack.com/archives/D0964BMSFDX/p1772538967387659",
    focusItems: [
      "Expérience utilisateur candidat & recruteur",
      "Design system & interfaces scalables",
      "Optimisation adoption & conversion",
      "Cohérence visuelle & fluidité parcours",
    ],
  },
];

const teamFocusCards = [
  {
    title: "Produit guidé par l'IA",
    body: "Chaque brique TAP est pensée avec une couche IA concrète : scoring, matching, recommandations et analyse continue des parcours.",
  },
  {
    title: "Expériences candidates premium",
    body: "Nous dessinons des parcours fluides, clairs et exigeants pour valoriser les talents au-delà du CV classique.",
  },
  {
    title: "Confiance des recruteurs",
    body: "Des décisions appuyées par la donnée, des interfaces lisibles et un accompagnement humain pour les équipes RH.",
  },
  {
    title: "Architecture prête à scaler",
    body: "Une plateforme pensée pour grandir : sécurité, performance et intégration dans les écosystèmes existants.",
  },
];

const IconLinkedIn = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      fill="currentColor"
      d="M4.98 3.5C4.98 4.88 3.88 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 4.98 2.12 4.98 3.5zM.23 8.32h4.55V24H.23V8.32zM8.54 8.32h4.36v2.13h.06c.61-1.15 2.1-2.36 4.32-2.36 4.62 0 5.47 3.04 5.47 6.99V24h-4.74v-7.6c0-1.81-.03-4.14-2.52-4.14-2.52 0-2.91 1.97-2.91 4v7.74H8.54V8.32z"
    />
  </svg>
);

function Team() {
  return (
    <section
      className="team-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="team-overlay" />
      <div className="team-inner">
        {/* SECTION ADN PRODUIT / 4 CARTES */}
        <section className="team-section-block team-focus-block">
          <div className="team-focus-layout">
            <div className="team-focus-text">
              <span className="team-section-kicker">L&apos;ÉQUIPE</span>
              <h2 className="team-section-title">
                Une équipe construite pour
                {" "}
                <span className="team-section-title-accent">livrer du concret</span>
              </h2>
              <p className="team-focus-subtitle">
                Tech, produit, design et opérationnel travaillent ensemble sur un objectif unique :
                faire de TAP une plateforme utile, fiable et désirable pour les talents comme pour les entreprises.
              </p>
            </div>

            <div className="team-focus-grid">
              {teamFocusCards.map((item) => (
                <article key={item.title} className="team-focus-card">
                  <h3 className="team-focus-card-title">{item.title}</h3>
                  <p className="team-focus-card-body">{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* SECTION FONDATEURS */}
        <section className="team-section-block">
          <header className="team-section-header">
            <span className="team-section-kicker">Leadership</span>
            <h2 className="team-section-title">
              Fondateurs
            </h2>
          </header>

          <div className="founders-layout">
            {founders.map((member, index) => (
              <article
                key={member.name}
                className="team-founder-card"
                style={{ animationDelay: `${0.1 + index * 0.1}s` }}
              >
                <div className="team-founder-media">
                  <img src={member.avatar} alt={member.name} />
                </div>
                <div className="team-founder-content">
                  <div className="team-founder-header">
                    <span className="team-founder-role-label">{member.role}</span>
                    <h3 className="team-founder-name">{member.name}</h3>
                    <p className="team-founder-description">
                      {member.focusItems[0]}
                    </p>
                  </div>

                  <ul className="team-founder-list">
                    {member.focusItems.slice(1).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>

                  <div className="team-founder-footer">
                    {member.linkedinUrl && (
                      <a
                        href={member.linkedinUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="team-founder-linkedin"
                        aria-label={`Profil LinkedIn de ${member.name}`}
                      >
                        <span className="team-link-icon">
                          <IconLinkedIn />
                        </span>
                        <span className="team-link-text">LinkedIn</span>
                        <span className="team-link-arrow">↗</span>
                      </a>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* SECTION ÉQUIPE OPÉRATIONNELLE */}
        <section className="team-section-block">
          <header className="team-section-header">
            <span className="team-section-kicker">Cœur de produit</span>
            <h2 className="team-section-title">
              Équipe <span className="team-section-title-accent">opérationnelle</span>
            </h2>
          </header>

          <div className="team-grid">
            {teamMembers.map((member, index) => (
              <article
                key={member.name}
                className="team-member-card"
                style={{ animationDelay: `${0.1 + index * 0.1}s` }}
              >
                <div className="team-member-content">
                  <div className="team-member-avatar-ring">
                    <div className="team-member-avatar">
                      <img src={member.avatar} alt={member.name} />
                    </div>
                  </div>

                  <div className="team-member-header">
                    <span className="team-member-role-label">{member.role}</span>
                    <h3 className="team-member-name">{member.name}</h3>
                    <p className="team-member-description">
                      {member.focusItems[0]}
                    </p>
                  </div>

                  <div className="team-member-footer">
                    {member.linkedinUrl && (
                      <a
                        href={member.linkedinUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="team-member-linkedin"
                        aria-label={`Profil LinkedIn de ${member.name}`}
                      >
                        <span className="team-link-icon">
                          <IconLinkedIn />
                        </span>
                        <span className="team-link-text">LinkedIn</span>
                        <span className="team-link-arrow">↗</span>
                      </a>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

      </div>
    </section>
  );
}

export default Team;

