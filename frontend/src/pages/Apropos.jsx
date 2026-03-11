import React from "react";
import "../css/Apropos.css";
import "../css/PourquoiTap.css";
import heroImage from "../assets/new-bgpages.jpg";
import {
  HiOutlineChartBar,
  HiOutlineBookOpen,
  HiOutlineFolderOpen,
  HiOutlineTrendingUp,
  HiOutlineBadgeCheck,
  HiOutlineSparkles,
  HiOutlineOfficeBuilding,
  HiOutlineUserGroup,
  HiOutlineArrowNarrowRight,
} from "react-icons/hi";

function About() {
  return (
    <section
      className="about-section"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="about-inner">
        {/* HERO */}
        <header className="about-hero">
          <div className="about-hero-main">
            <span className="about-hero-tag">À propos</span>
            <h1 className="about-hero-title">
              À propos de <span className="about-hero-title-accent">TAP</span>
            </h1>
            <p className="about-hero-subtitle">
              Elever chaque talent au niveau d’exigence des meilleures entreprises.
            </p>
            <p className="about-hero-desc">
              TAP orchestre l&apos;analyse de CV, le scoring d&apos;employabilité et le micro‑learning pour transformer des
              profils prometteurs en candidats immédiatement opérationnels.
            </p>
          </div>

          <div className="about-hero-metrics">
            <div className="about-metric-card">
              <span className="about-metric-value">4</span>
              <span className="about-metric-label">axes clés</span>
            </div>
            <div className="about-metric-card">
              <span className="about-metric-value">IA</span>
              <span className="about-metric-label">au cœur du scoring</span>
            </div>
            <div className="about-metric-card">
              <span className="about-metric-value">100%</span>
              <span className="about-metric-label">focus employabilité</span>
            </div>
          </div>
        </header>

        {/* SECTION VALEUR AJOUTÉE */}
        <section className="about-section-block">
          <header className="about-section-header">
            <span className="about-section-kicker">Notre valeur ajoutée</span>
            <h2 className="about-section-title">
              Réconcilier le <span className="about-section-title-accent">potentiel</span> avec le marché.
            </h2>
          </header>

          <div className="about-value-grid">
            <article className="about-value-card">
              <h3>
                <span className="about-value-icon">
                  <HiOutlineBadgeCheck />
                </span>
                <span>Notre mission</span>
              </h3>
              <p>
                Réduire l’écart entre ce que les talents savent faire et ce que les entreprises attendent vraiment, en rendant
                l’employabilité lisible et actionnable.
              </p>
            </article>
            <article className="about-value-card">
              <h3>
                <span className="about-value-icon">
                  <HiOutlineSparkles />
                </span>
                <span>Notre approche</span>
              </h3>
              <p>
                Une plateforme unique qui combine scoring fin, micro‑learning ciblé et portfolio vivant pour documenter et faire
                progresser chaque parcours.
              </p>
            </article>
          </div>
        </section>

        {/* SECTION FONDATIONS */}
        <section className="about-section-block about-foundations">
          <header className="about-section-header">
            <span className="about-section-kicker">Notre promesse</span>
            <h2 className="about-section-title">
              Les fondations de <span className="about-section-title-accent">TAP</span>
            </h2>
          </header>

          <div className="about-foundations-grid">
            <article className="about-foundation">
              <div className="about-foundation-icon">
                <span className="about-foundation-icon-glyph">
                  <HiOutlineChartBar />
                </span>
              </div>
              <h3>Diagnostic précis</h3>
              <p>Une lecture fine du profil au‑delà du CV, portée par la donnée et l’IA.</p>
            </article>
            <article className="about-foundation">
              <div className="about-foundation-icon">
                <span className="about-foundation-icon-glyph">
                  <HiOutlineBookOpen />
                </span>
              </div>
              <h3>Micro‑learning</h3>
              <p>Des capsules ciblées sur les écarts concrets observés sur le terrain.</p>
            </article>
            <article className="about-foundation">
              <div className="about-foundation-icon">
                <span className="about-foundation-icon-glyph">
                  <HiOutlineFolderOpen />
                </span>
              </div>
              <h3>Portfolio vivant</h3>
              <p>Un dossier dynamique qui suit et prouve la progression de chaque talent.</p>
            </article>
            <article className="about-foundation">
              <div className="about-foundation-icon">
                <span className="about-foundation-icon-glyph">
                  <HiOutlineTrendingUp />
                </span>
              </div>
              <h3>Score transparent</h3>
              <p>Un score d’employabilité clair, partagé entre talents et recruteurs.</p>
            </article>
          </div>
        </section>

        {/* SECTION AUDIENCES */}
        <section className="about-section-block about-audiences">
          <header className="about-section-header">
            <span className="about-section-kicker">Audiences</span>
            <h2 className="about-section-title">
              Pour <span className="about-section-title-accent">qui&nbsp;?</span>
            </h2>
          </header>

          <div className="about-audience-grid">
            <article className="about-audience-card about-audience-card--left">
              <header className="about-audience-header">
                <span className="about-audience-chip">
                  <HiOutlineOfficeBuilding />
                  <span>Entreprises</span>
                </span>
                <span className="about-audience-arrow">
                  <HiOutlineArrowNarrowRight />
                </span>
              </header>
              <ul className="about-audience-list">
                <li>Recrutement précis, guidé par les données et l’IA.</li>
                <li>Candidats acculturés, opérationnels dès le jour 1.</li>
                <li>Meilleure rétention grâce à l’accompagnement en amont.</li>
              </ul>
            </article>

            <article className="about-audience-card about-audience-card--right">
              <header className="about-audience-header">
                <span className="about-audience-chip">
                  <HiOutlineUserGroup />
                  <span>Talents</span>
                </span>
                <span className="about-audience-arrow">
                  <HiOutlineArrowNarrowRight />
                </span>
              </header>
              <ul className="about-audience-list">
                <li>Jeunes diplômés à haut potentiel.</li>
                <li>Profils en reconversion ambitieuse.</li>
                <li>Talents tech et métiers d’avenir.</li>
              </ul>
              <p className="about-audience-note">100&nbsp;% gratuit pour les candidats.</p>
            </article>
          </div>
        </section>
      </div>
    </section>
  );
}

export default About;
