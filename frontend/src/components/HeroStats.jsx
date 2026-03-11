import React from "react";
import "../css/HeroStats.css";

const STATS = [
  { value: "80%", text: "Des candidatures sont filtrées avant lecture humaine." },
  { value: "45%", text: "Des diplômés restent invisibles faute de preuves concrètes." },
  { value: "35%", text: "Des talents quittent leur poste faute d’accompagnement." },
  { value: "100+", text: "Profils accompagnés par TAP sur leur trajectoire." },
];

const HeroStats = () => {
  return (
    <section className="hero-stats">
      <div className="hero-stats-inner">
        <header className="hero-stats-header">
          <span className="hero-stats-kicker">La situation</span>
          <h2 className="hero-stats-title">
            Rejetés avant d&apos;être{" "}
            <span className="hero-stats-title-accent">compris.</span>
          </h2>
        </header>
        <div className="hero-cards hero-cards--grid">
          {STATS.map((item, index) => (
            <article key={item.text} className="hero-stat-card">
              <div className="hero-stat-value">
                {item.value}
              </div>
              <p className="hero-stat-text">{item.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HeroStats;

