import React, { useState, useEffect, useRef } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import "../css/Header.css";
import logo from "../assets/logo.svg";

const Header = () => {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const navRef = useRef(null);
  const burgerRef = useRef(null);

  useEffect(() => {
    if (!menuOpen) return;

    const handleClick = (event) => {
      const nav = navRef.current;
      const burger = burgerRef.current;
      if (!nav || !burger) return;
      if (nav.contains(event.target) || burger.contains(event.target)) {
        return;
      }
      setMenuOpen(false);
    };

    const handleScroll = () => {
      setMenuOpen(false);
    };

    document.addEventListener("click", handleClick);
    window.addEventListener("scroll", handleScroll);

    return () => {
      document.removeEventListener("click", handleClick);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [menuOpen]);

  return (
    <header className="header">
      <div className="header-container">
        
        {/* Logo */}
        <div className="logo" onClick={() => navigate("/")}>
          <img src={logo} alt="Logo" />
        </div>

        {/* Hamburger (mobile) */}
        <div
          className="hamburger"
          ref={burgerRef}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          ☰
        </div>

        {/* Navigation */}
        <nav className={`nav ${menuOpen ? "open" : ""}`} ref={navRef}>
         <ul>
  <li>
    <NavLink to="/" end onClick={() => setMenuOpen(false)}>
      Accueil
    </NavLink>
  </li>

  <li>
    <NavLink to="/a-propos" onClick={() => setMenuOpen(false)}>
      À propos
    </NavLink>
  </li>

  <li>
    <NavLink to="https://demo.tap-hr.com/" onClick={() => setMenuOpen(false)}>
      Démo
    </NavLink>
  </li>

  <li>
    <NavLink to="/team" onClick={() => setMenuOpen(false)}>
      Team
    </NavLink>
  </li>

  <li>
    <NavLink to="/contact" onClick={() => setMenuOpen(false)}>
      Contact
    </NavLink>
  </li>
</ul>

          {/* Boutons visibles en mobile dans le menu */}
          <div className="nav-buttons-mobile">
            <button
              className="login-btn"
              onClick={() => {
                setMenuOpen(false);
                navigate("/connexion");
              }}
            >
              Se connecter
            </button>
            <button
              className="signup-btn"
              onClick={() => { setMenuOpen(false); navigate("/creer-compte"); }}
            >
              Créer mon profil
            </button>
          </div>
        </nav>

        {/* Buttons (desktop) */}
        <div className="header-buttons">
          <button className="login-btn" onClick={() => navigate("/connexion")}>
            Se connecter
          </button>

          <button 
            className="signup-btn"
            onClick={() => navigate("/creer-compte")}
          >
            Créer mon profil
          </button>
        </div>

      </div>
    </header>
  );
};

export default Header;