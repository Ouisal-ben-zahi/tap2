import React from "react";
import "../css/Accueil.css";
import Hero from "../components/Hero";
import PourquoiTap from "../components/PourquoiTap";
import TalentSection from "../components/CommentCaMarche";

const Accueil = () => {
  return (
    <div className="page-accueil">
      <Hero />
      <PourquoiTap />
      <TalentSection />
    </div>
  );
};

export default Accueil; 