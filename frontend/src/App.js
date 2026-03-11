import React, { useEffect } from "react";
import './App.css';
import { BrowserRouter as Router, Routes, Route, useLocation } from "react-router-dom";
import Header from './layout/Header';
import Home from "./pages/Accueil";
import About from "./pages/Apropos";
import Team from "./pages/Team";
import Blog from "./pages/Blog";
import Connexion from "./pages/Connexion";
import CreerCompte from "./pages/CreerCompte";
import Contact from "./pages/Contact";
import MentionsLegales from "./pages/MentionsLegales";
import PolitiqueConfidentialite from "./pages/PolitiqueConfidentialite";
import ConditionsUtilisation from "./pages/ConditionsUtilisation";
import DashboardCandidat from "./pages/DashboardCandidat";
import DashboardRecruteur from "./pages/DashboardRecruteur";
import Footer from './layout/Footer';

function AppShell() {
  const location = useLocation();

  const isDashboard = location.pathname.startsWith("/dashboard");

  // Scroll en haut à chaque changement de page (header, footer, liens internes)
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [location.pathname]);

  if (isDashboard) {
    // Pas de header / footer pour les pages dashboard
    return (
      <Routes>
        <Route path="/dashboard-candidat" element={<DashboardCandidat />} />
        <Route path="/dashboard-recruteur" element={<DashboardRecruteur />} />
      </Routes>
    );
  }

  return (
    <>
      <Header />
      <div className="app-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/a-propos" element={<About />} />
          <Route path="/team" element={<Team />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/connexion" element={<Connexion />} />
          <Route path="/creer-compte" element={<CreerCompte />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/mentions-legales" element={<MentionsLegales />} />
          <Route
            path="/politique-confidentialite"
            element={<PolitiqueConfidentialite />}
          />
          <Route
            path="/conditions-utilisation"
            element={<ConditionsUtilisation />}
          />
        </Routes>
      </div>
      <Footer />
    </>
  );
}

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

export default App;