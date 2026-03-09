import React, { useRef, useState, useEffect } from "react";
import "../css/HeroStats.css";
import cardIcon from "../assets/path20.svg";

const stats = [
  {
    value: "80%",
    text: "Des candidatures sont filtrées avant lecture humaine.",
  },
  {
    value: "45%",
    text: "Des diplômés restent invisibles faute de preuves concrètes.",
  },
  {
    value: "35%",
    text: "Des talents quittent leur poste faute d’accompagnement.",
  },
];

const HeroStats = () => {
  const [activeCard, setActiveCard] = useState(0);
  const cardsRef = useRef(null);
  const autoScrollRef = useRef(null);
  const [autoScrollActive, setAutoScrollActive] = useState(true);

  const handleScroll = () => {
    const el = cardsRef.current;
    if (!el) return;
    const width = el.clientWidth || 1;
    const index = Math.round(el.scrollLeft / width);
    setActiveCard(Math.max(0, Math.min(stats.length - 1, index)));
  };

  const stopAutoScroll = () => {
    if (!autoScrollActive) return;
    setAutoScrollActive(false);
    if (autoScrollRef.current) {
      clearInterval(autoScrollRef.current);
      autoScrollRef.current = null;
    }
  };

  useEffect(() => {
    const el = cardsRef.current;
    if (!el) return;

    if (window.innerWidth > 768 || !autoScrollActive) return;

    autoScrollRef.current = setInterval(() => {
      const width = el.clientWidth || 1;
      setActiveCard((prev) => {
        const next = (prev + 1) % stats.length;
        el.scrollTo({
          left: next * width,
          behavior: "smooth",
        });
        return next;
      });
    }, 2000);

    return () => {
      if (autoScrollRef.current) {
        clearInterval(autoScrollRef.current);
        autoScrollRef.current = null;
      }
    };
  }, [autoScrollActive]);

  return (
    <section className="hero-stats">
      <div className="hero-stats-inner">
        <h2 className="hero-stats-title">Rejetés avant d&apos;être compris.</h2>
        <div
          className="hero-cards"
          ref={cardsRef}
          onScroll={handleScroll}
          onMouseEnter={stopAutoScroll}
          onTouchStart={stopAutoScroll}
          onClick={stopAutoScroll}
        >
          {stats.map((item, index) => (
            <div
              key={index}
              className={
                "hero-stat-card" + (activeCard === index ? " active" : "")
              }
            >
              <img src={cardIcon} alt="" className="hero-stat-icon" />
              <div className="hero-stat-value">{item.value}</div>
              <p className="hero-stat-text">{item.text}</p>
            </div>
          ))}
        </div>

        <div className="hero-dots">
          {stats.map((_, index) => (
            <span
              key={index}
              className={
                "hero-dot" + (activeCard === index ? " active" : "")
              }
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default HeroStats;

