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

function Team() {
  return (
    <section
      className="team-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="team-overlay" />
      <div className="team-inner">
        {/* HERO + MÉTRIQUES */}
        <header className="team-hero">
          <div className="team-hero-top">
            <span className="team-hero-tag">L&apos;ÉQUIPE</span>

            <div className="team-hero-title-block">
              <h1 className="team-hero-title">
                L&apos;équipe <span className="team-hero-title-accent">TAP</span>
              </h1>
              <p className="team-hero-subtitle">
                Tech, stratégie et design réunis pour transformer l&apos;employabilité au Maroc.
              </p>
            </div>
          </div>

          <div className="team-hero-metrics">
            <div className="team-metric-card team-metric-card--1">
              <span className="team-metric-value">2</span>
              <span className="team-metric-label">Fondateurs</span>
            </div>
            <div className="team-metric-card team-metric-card--2">
              <span className="team-metric-value">{founders.length + teamMembers.length}</span>
              <span className="team-metric-label">Membres</span>
            </div>
            <div className="team-metric-card team-metric-card--3">
              <span className="team-metric-value">100%</span>
              <span className="team-metric-label">Maroc</span>
            </div>
          </div>
        </header>

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
                        LinkedIn ↗
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
                        LinkedIn ↗
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

