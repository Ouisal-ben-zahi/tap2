import React, { useState } from "react";
import "../css/Faq.css";

const faqs = [
  {
    question: "Qu’est‑ce que TAP pour une entreprise exigeante ?",
    answer:
      "TAP est une plateforme de sélection augmentée par l’IA : elle révèle le vrai potentiel des talents, avant même l’entretien, et vous livre des profils déjà structurés, scorés et prêts à être évalués.",
  },
  {
    question: "Pourquoi les recruteurs choisissent‑ils TAP plutôt qu’un jobboard classique ?",
    answer:
      "Parce que vous ne recevez pas des CV, mais des dossiers de talents préparés : analyse IA, score d’employabilité, preuves de compétences et accompagnement en amont pour sécuriser chaque recrutement.",
  },
  {
    question: "Quel est le modèle économique de TAP ?",
    answer:
      "Les recruteurs et entreprises financent la plateforme lorsqu’ils sourcent ou recrutent via TAP. Ce choix garantit une expérience 100 % gratuite et exigeante pour les talents.",
  },
  {
    question: "TAP est‑il vraiment gratuit pour les candidats ?",
    answer:
      "Oui. Les talents accèdent gratuitement aux parcours, aux recommandations IA et aux opportunités. L’investissement est porté par les entreprises qui recherchent ce niveau de préparation et de fiabilité.",
  },
  {
    question: "Quel niveau d’accompagnement proposez‑vous aux talents ?",
    answer:
      "Chaque talent bénéficie de recommandations personnalisées, de micro‑learning ciblé et d’un suivi continu. L’objectif est simple : présenter aux recruteurs des profils alignés, confiants et immédiatement opérationnels.",
  },
];

const Faq = () => {
  const [openIndex, setOpenIndex] = useState(0);

  const toggle = (index) => {
    setOpenIndex((prev) => (prev === index ? -1 : index));
  };

  return (
    <section className="faq-section">
      <div className="faq-inner">
        <header className="faq-header">
          <span className="faq-kicker">Questions fréquentes</span>
          <h2 className="faq-title">
            Comprendre <span className="faq-title-accent">TAP.</span>
          </h2>
          <p className="faq-subtitle">
            Tout ce qu’il faut savoir pour intégrer TAP dans votre stratégie
            talent.
          </p>
        </header>

        <div className="faq-grid">
          {faqs.map((item, index) => {
            const isOpen = openIndex === index;
            return (
              <article
                key={item.question}
                className={
                  "faq-item" + (isOpen ? " faq-item--open" : "")
                }
                style={{ animationDelay: `${0.12 + index * 0.06}s` }}
              >
                <button
                  type="button"
                  className="faq-question"
                  onClick={() => toggle(index)}
                >
                  <span className="faq-question-text">{item.question}</span>
                  <span className="faq-question-icon">
                    {isOpen ? "−" : "+"}
                  </span>
                </button>
                <div className="faq-answer-wrapper">
                  <p className="faq-answer">{item.answer}</p>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default Faq;

