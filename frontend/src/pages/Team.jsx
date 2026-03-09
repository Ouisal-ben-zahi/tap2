import React from "react";
import "../css/Team.css";
import heroImage from "../assets/new-bgpages.jpg";
import imadAvatar from "../assets/imad-el-boukhiari.png";
import zakariaAvatar from "../assets/zakaria-Ajmil.png";
import hajarAvatar from "../assets/Hajar-el-aouni.jpg";
import jawharAvatar from "../assets/Juwher Profil.jpg";
import ouissalAvatar from "../assets/Ouissal-ben-zahi.jpg";
import "../css/PourquoiTap.css"

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
  const allMembers = [...founders, ...teamMembers];

  return (
    <section
      className="team-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="team-inner">
        <header className="team-header">
          <div className="team-heading">
            <div className="team-heading-main">L&apos;ÉQUIPE TAP</div>
            <div className="team-heading-sub">
              Une équipe fondatrice et opérationnelle réunie autour d&apos;une ambition commune&nbsp;:
              <br />
              élever les standards de l&apos;employabilité.
            </div>
          </div>
          <p className="team-intro">
            TAP est portée par deux co‑fondateurs et une équipe cœur mêlant produit, IA, design et
            ingénierie, pour concevoir une expérience à la fois exigeante, fluide et profondément
            utile aux talents comme aux entreprises.
          </p>
        </header>

        <div className="team-list">
          {allMembers.map((member, index) => (
            <div
              key={member.name}
              className={`team-row ${index % 2 === 1 ? "team-row-alt" : ""}`}
            >
              <article className="team-card">
                <div className="team-avatar">
                  {member.avatar ? (
                    <img src={member.avatar} alt={member.name} />
                  ) : (
                    <span>
                      {member.name
                        .split(" ")
                        .map((part) => part[0])
                        .join("")}
                    </span>
                  )}
                </div>
                <div className="team-card-body">
                  <div className="team-card-header">
                    <div className="team-name-block">
                      <h2>{member.name}</h2>
                      <p className="team-role">{member.role}</p>
                    </div>
                    {member.linkedinUrl && (
                      <a
                        href={member.linkedinUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="team-linkedin-icon"
                        aria-label={`Profil LinkedIn de ${member.name}`}
                      >
                        in
                      </a>
                    )}
                  </div>

                  {Array.isArray(member.focusItems) && member.focusItems.length > 0 && (
                    <div className="team-focus-multi">
                      {member.focusItems.map((item) => (
                        <p key={item} className="team-focus-line">
                          {item}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default Team;

