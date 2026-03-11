import React from "react";
import "../css/Hero.css";
import africaMapImg from "../assets/Africa-Map.png";

/* ─────────────────────────────────────────────
   MAIN COMPONENT — Hero
───────────────────────────────────────────── */
function Hero() {
  return (
    <section className="hero-section">
      {/* Background image */}
      <div className="hero-bg" />

      {/* Overlay : black left → transparent right */}
      <div className="hero-overlay" />
      <div className="hero-overlay-vignette" />

      {/* Inner layout */}
      <div className="hero-inner">
        {/* ── LEFT : text content ── */}
        <div className="hero-content">
          {/* Tag en haut comme les autres sections */}
          <div className="hero-badge">Plateforme IA — Maroc</div>

          {/* Title */}
          <h1 className="hero-title">
            <span className="hero-title-line">
              Des profils. Des{" "}
              <span className="hero-title-strong">talents</span>.
            </span>
            <span className="hero-title-line">
              Prêts à{" "}
              <span className="hero-title-accent" data-text="performer">
                performer
              </span>
              .
            </span>
          </h1>

          {/* Description */}
          <p className="hero-desc">
            L'IA qui analyse, forme et connecte les candidats aux
            entreprises qui recrutent au Maroc.
          </p>

          {/* CTAs */}
          <div className="hero-buttons">
            <a href="#decouvrir" className="hero-btn-primary">
              Découvrir TAP
              <span className="hero-btn-primary-arrow">→</span>
            </a>
            <a href="#profil" className="hero-btn-secondary">
              Créer mon profil
            </a>
          </div>
        </div>

        {/* ── RIGHT : Africa map ── (positioned absolute) */}
      </div>

      {/* Map image placée à droite */}
      <div className="hero-map-container">
        <img src={africaMapImg} alt="" className="hero-map-svg" aria-hidden="true" />
      </div>
    </section>
  );
}

export default Hero;
