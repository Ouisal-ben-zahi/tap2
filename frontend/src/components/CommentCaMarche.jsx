import React from "react";
import "../css/TalentSection.css";
import {
  HiOutlineUserAdd,
  HiOutlineChartSquareBar,
  HiOutlineBookOpen,
  HiOutlineOfficeBuilding,
} from "react-icons/hi";

const steps = [
  {
    id: "01",
    icon: <HiOutlineUserAdd />,
    title: "Inscription",
    desc: "Créez votre profil candidat en quelques minutes et uploadez votre CV.",
  },
  {
    id: "02",
    icon: <HiOutlineChartSquareBar />,
    title: "Analyse IA",
    desc: "Notre IA identifie vos forces, compétences et axes d’amélioration.",
  },
  {
    id: "03",
    icon: <HiOutlineBookOpen />,
    title: "Formation",
    desc: "Micro‑learning ciblé et personnalisé pour monter en compétence rapidement.",
  },
  {
    id: "04",
    icon: <HiOutlineOfficeBuilding />,
    title: "Matching",
    desc: "Votre profil validé rencontre les recruteurs qui embauchent au Maroc.",
  },
];

const TalentSection = () => {
  return (
    <section className="main-section">
      <div className="content-container">
        <header className="process-header">
          <span className="process-kicker">Le processus</span>
          <h2 className="process-title">
            Comment <span className="process-title-accent">ça marche</span>
          </h2>
        </header>

        <div className="process-grid process-grid--vertical">
          <div className="process-vertical-line" />
          {steps.map((step, index) => {
            const isLeft = index % 2 === 0;
            return (
              <div
                key={step.id}
                className="process-row"
                style={{ animationDelay: `${0.15 + index * 0.06}s` }}
              >
                <div
                  className={
                    "process-side " +
                    (isLeft ? "process-side--content" : "process-side--empty")
                  }
                >
                  {isLeft && (
                    <article className="process-item process-item--left">
                      <h3 className="process-item-title">{step.title}</h3>
                      <p className="process-item-desc">{step.desc}</p>
                    </article>
                  )}
                </div>

                <div className="process-center">
                  <div className="process-center-dot-outer">
                    <div className="process-center-dot-inner" />
                  </div>
                </div>

                <div
                  className={
                    "process-side " +
                    (!isLeft ? "process-side--content" : "process-side--empty")
                  }
                >
                  {!isLeft && (
                    <article className="process-item process-item--right">
                      <h3 className="process-item-title">{step.title}</h3>
                      <p className="process-item-desc">{step.desc}</p>
                    </article>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default TalentSection;