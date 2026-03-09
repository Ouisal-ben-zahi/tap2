import React from 'react';
import '../css/TalentSection.css';

const TalentSection = () => {
  const steps = [
    { id: "01", text: "LE CANDIDAT CRÉE SON PROFIL" },
    { id: "02", text: "L'IA ANALYSE ET IDENTIFIE LES ÉCARTS" },
    { id: "03", text: "TAP AIDE À AMÉLIORER LE NIVEAU" },
    { id: "04", text: "LE PROFIL DEVIENT VISIBLE AUX ENTREPRISES" },
  ];

  return (
    <section 
      className="main-section" 
     
    >
      <div className="content-container">
        <h2 className="main-title">COMMENT ÇA MARCHE</h2>

        <div className="steps-grid">
          {steps.map((step, index) => (
            <div key={index} className="step-item">
              <div className="step-number">{step.id}</div>
              <div className="step-text">{step.text}</div>
            </div>
          ))}
        </div>

        <div className="cta-section">
          <h2 className="cta-title">PRÊT À RECRUTER DES TALENTS DÉJÀ PRÉPARÉS ?</h2>
          <div className="button-group">
            <button className="btn-red">ACCÉDER AUX TALENTS</button>
            <button className="btn-outline">CRÉER MON PROFIL</button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default TalentSection;