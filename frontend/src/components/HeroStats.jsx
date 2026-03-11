import React, { useEffect, useRef, useState } from "react";
import "../css/HeroStats.css";

const STATS = [
  { value: 80, suffix: "%", text: "Des candidatures sont filtrées avant lecture humaine." },
  { value: 45, suffix: "%", text: "Des diplômés restent invisibles faute de preuves concrètes." },
  { value: 35, suffix: "%", text: "Des talents quittent leur poste faute d’accompagnement." },
  { value: 100, suffix: "+", text: "Profils accompagnés par TAP sur leur trajectoire." },
];

const AnimatedCounter = ({ end, active, delay = 0, duration = 1200 }) => {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!active) return;
    let startTime;

    const step = (ts) => {
      if (!startTime) startTime = ts;
      const t = ts - startTime - delay;
      if (t < 0) {
        requestAnimationFrame(step);
        return;
      }
      const progress = Math.min(t / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setValue(Math.round(end * eased));
      if (progress < 1) requestAnimationFrame(step);
    };

    const id = requestAnimationFrame(step);
    return () => cancelAnimationFrame(id);
  }, [active, end, delay, duration]);

  return <>{value}</>;
};

const HeroStats = () => {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <section className="hero-stats" ref={ref}>
      <div className="hero-stats-inner">
        <header className="hero-stats-header">
          <span className="hero-stats-kicker">La situation</span>
          <h2 className="hero-stats-title">
            Rejetés avant d&apos;être{" "}
            <span className="hero-stats-title-accent">compris.</span>
          </h2>
        </header>
        <div className="hero-cards hero-cards--grid">
          {STATS.map((item, index) => (
            <article key={item.text} className="hero-stat-card">
              <div className="hero-stat-value">
                <AnimatedCounter
                  end={item.value}
                  active={visible}
                  delay={index * 150}
                />
                {item.suffix}
              </div>
              <p className="hero-stat-text">{item.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HeroStats;

