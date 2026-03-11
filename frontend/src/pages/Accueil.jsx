import React from "react";
import "../css/Accueil.css";
import Hero from "../components/Hero";
import PourquoiTap from "../components/PourquoiTap";
import TalentSection from "../components/CommentCaMarche";
import Faq from "../components/Faq";

const Accueil = () => {
  return (
    <div className="page-accueil">
      <Hero />
      <PourquoiTap />
      <TalentSection />
      <Faq />
    </div>
  );
};

export default Accueil; 