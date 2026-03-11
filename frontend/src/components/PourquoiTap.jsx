import React from "react";
import "../css/PourquoiTap.css";
import HeroStats from "./HeroStats";
import {
  HiOutlineChip,
  HiOutlineBadgeCheck,
  HiOutlineBookOpen,
  HiOutlineSwitchHorizontal,
} from "react-icons/hi";

const cards = [
  {
    title: "Analyse IA",
    metric: "<30s d’analyse",
    icon: HiOutlineChip,
    tone: "red",
    body:
      "Chaque CV est scanné et évalué par notre moteur d’intelligence artificielle en moins de 30 secondes.",
  },
  {
    title: "Score d’employabilité",
    metric: "0–100 score",
    icon: HiOutlineBadgeCheck,
    tone: "light",
    body:
      "Un score objectif de 0 à 100 basé sur les compétences réelles, pas les diplômes.",
  },
  {
    title: "Micro‑learning",
    metric: "37+ modules",
    icon: HiOutlineBookOpen,
    tone: "red",
    body:
      "Des formations courtes et ciblées pour combler les lacunes identifiées par l’IA.",
  },
  {
    title: "Matching intelligent",
    metric: "87% précision",
    icon: HiOutlineSwitchHorizontal,
    tone: "light",
    body:
      "Les profils validés sont connectés aux recruteurs qui embauchent, en temps réel.",
  },
];

const PourquoiTap = () => {
  return (
    <section className="pourquoi-section">
            <HeroStats />
      
      <div className="pourquoi-inner">
        <header className="pourquoi-header">
          <span className="pourquoi-kicker">La solution</span>
          <h2 className="pourquoi-title">
            Pourquoi <span className="pourquoi-title-accent">TAP&nbsp;?</span>
          </h2>
          <p className="pourquoi-subtitle">
            Chaque candidat visible sur TAP passe par une analyse, une préparation et un scoring exigeants.
          </p>
        </header>

        {/* Grille 2x2 des cartes comme sur la maquette */}
        <section className="pourquoi-cards-section">
          <div className="pourquoi-cards-grid">
            {cards.map((card, index) => (
              <article
                key={card.title}
                className={
                  "pourquoi-card " +
                  (card.tone === "red"
                    ? "pourquoi-card--red"
                    : "pourquoi-card--light")
                }
                style={{ animationDelay: `${0.15 + index * 0.06}s` }}
              >
                <header className="pourquoi-card-header">
                  <span className="pourquoi-card-icon" aria-hidden="true">
                    {card.icon ? <card.icon /> : null}
                  </span>
                  <div className="pourquoi-card-meta">
                    <p className="pourquoi-card-metric">{card.metric}</p>
                  </div>
                </header>
                <div className="pourquoi-card-body">
                  <h3 className="pourquoi-card-title">{card.title}</h3>
                  <p className="pourquoi-card-text">{card.body}</p>
                  <button className="pourquoi-card-link" type="button">
                    En savoir plus →
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
};

export default PourquoiTap;