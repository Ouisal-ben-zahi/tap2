import React, { useState } from "react";
import './App.css';
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Header from './layout/Header';
import Home from "./pages/Accueil";
import About from "./pages/Apropos";
import Team from "./pages/Team";
import Blog from "./pages/Blog";
import Connexion from "./pages/Connexion";
import CreerCompte from "./pages/CreerCompte";
import Contact from "./pages/Contact";
import Footer from './layout/Footer';
import CountdownPopup from "./components/CountdownPopup";

function App() {
  const [showCountdownPopup, setShowCountdownPopup] = useState(true);

  return (
    <Router>
      {showCountdownPopup && (
        <CountdownPopup onClose={() => setShowCountdownPopup(false)} />
      )}
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
        </Routes>
      </div>
      <Footer />
    </Router>
  );
}

export default App;