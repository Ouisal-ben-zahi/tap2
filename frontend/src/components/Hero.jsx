import React from "react";
import "../css/Hero.css";
import africaMapImg from "../assets/carte map transparent.png";

/* ─────────────────────────────────────────────
   MAIN COMPONENT — Hero
───────────────────────────────────────────── */
function Hero() {
  return (
    <section className="hero-section">
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

        {/* ── RIGHT : Africa map ── */}
      </div>

      {/* Map image placée à droite + effet Marrakech premium */}
      <div className="hero-map-container">
        <img
          src={africaMapImg}
          alt=""
          className="hero-map-svg"
          aria-hidden="true"
        />

        {/* Point Marrakech avec pulsation concentrique */}
        <div className="hero-map-marker">
          <span className="hero-map-pulse" />
          <span className="hero-map-dot" />

          {/* Couronne de lignes lumineuses qui rayonnent comme un soleil */}
          <div className="hero-circle-stream">
            <span className="hero-circle hero-circle--1" />
            <span className="hero-circle hero-circle--2" />
            <span className="hero-circle hero-circle--3" />
            <span className="hero-circle hero-circle--4" />
            <span className="hero-circle hero-circle--5" />
            <span className="hero-circle hero-circle--6" />
            <span className="hero-circle hero-circle--7" />
            <span className="hero-circle hero-circle--8" />
          </div>
        </div>
      </div>
    </section>
  );
}

export default Hero;
