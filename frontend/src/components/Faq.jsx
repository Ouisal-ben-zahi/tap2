import React, { useState } from "react";
import "../css/Faq.css";

const faqs = [
  {
    question: "Qu’est‑ce que TAP concrètement ?",
    answer:
      "TAP est une plateforme qui analyse les profils avec l’IA, prépare les candidats et les connecte aux recruteurs sur la base de compétences réelles.",
  },
  {
    question: "Comment les candidats sont‑ils évalués ?",
    answer:
      "Chaque profil passe par une analyse IA, des modules de micro‑learning ciblés et l’obtention d’un score d’employabilité de 0 à 100.",
  },
  {
    question: "TAP remplace‑t‑il mon processus de recrutement ?",
    answer:
      "Non. TAP renforce votre processus actuel en vous donnant accès à des talents déjà préparés, scorés et accompagnés.",
  },
  {
    question: "Combien ça coûte pour les talents ?",
    answer:
      "L’accès à TAP est 100 % gratuit pour les candidats. Les entreprises financent la plateforme lorsqu’elles recrutent via TAP.",
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

