import React, { useState, useEffect, useRef } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import "../css/Header.css";
import logo from "../assets/logo-white.svg";

const Header = () => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const navigate = useNavigate();
  const navRef = useRef(null);
  const burgerRef = useRef(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;

    const handleClick = (e) => {
      if (
        navRef.current?.contains(e.target) ||
        burgerRef.current?.contains(e.target)
      ) return;
      setMenuOpen(false);
    };

    document.addEventListener("click", handleClick);
    window.addEventListener("scroll", () => setMenuOpen(false));

    return () => {
      document.removeEventListener("click", handleClick);
    };
  }, [menuOpen]);

  return (
    <header className={`header ${scrolled ? "header--scrolled" : ""}`}>
      <div className="header-container">

        {/* Logo */}
        <div className="logo" onClick={() => navigate("/")}>
          <img src={logo} alt="TAP – Talent Acceleration Platform" />
        </div>

        {/* Hamburger (mobile) */}
        <div
          className="hamburger"
          ref={burgerRef}
          onClick={() => setMenuOpen((o) => !o)}
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

            {/* Produit — hover déclenche le menu */}
            <li className="nav-item-product">
              <button type="button" className="nav-product-select">
                <span>Produit</span>
                <span className="nav-product-caret">▾</span>
              </button>
              <ul className="nav-product-menu">
                <li onClick={() => { navigate("/produit/analyse-cv"); setMenuOpen(false); }}>
                  Analyse IA du CV
                </li>
                <li onClick={() => { navigate("/produit/score"); setMenuOpen(false); }}>
                  Score d&apos;employabilité
                </li>
                <li onClick={() => { navigate("/produit/micro-learning"); setMenuOpen(false); }}>
                  Micro-learning
                </li>
                <li onClick={() => { navigate("/produit/matching"); setMenuOpen(false); }}>
                  Matching intelligent
                </li>
              </ul>
            </li>

            <li>
              <NavLink to="/team" onClick={() => setMenuOpen(false)}>
                Équipe
              </NavLink>
            </li>

            <li>
              <NavLink to="/contact" onClick={() => setMenuOpen(false)}>
                Contact
              </NavLink>
            </li>
          </ul>

          {/* Boutons visibles uniquement en mobile */}
          <div className="nav-buttons-mobile">
            <button
              className="signup-btn"
              onClick={() => {
                setMenuOpen(false);
                navigate("/connexion");
              }}
            >
              Se connecter
            </button>
          </div>
        </nav>

        {/* Boutons desktop */}
        <div className="header-buttons">
          <button
            className="signup-btn"
            onClick={() => navigate("/connexion")}
          >
            Se connecter
          </button>
        </div>

      </div>
    </header>
  );
};

export default Header;
