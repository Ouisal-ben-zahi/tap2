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

        <div className="process-grid">
          <div className="process-line" />
          {steps.map((step, index) => (
            <article
              key={step.id}
              className="process-item"
              style={{ animationDelay: `${0.15 + index * 0.06}s` }}
            >
              <div className="process-icon-wrapper">
                <div className="process-icon-ring">
                  <div className="process-icon">{step.icon}</div>
                </div>
              </div>
              <h3 className="process-item-title">{step.title}</h3>
              <p className="process-item-desc">{step.desc}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default TalentSection;