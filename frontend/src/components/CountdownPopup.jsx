import React, { useEffect } from "react";
import Countdown from "./Countdown";
import "../css/CountdownPopup.css";

const CountdownPopup = ({ onClose }) => {
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  return (
    <div className="countdown-popup-overlay" onClick={onClose}>
      <div
        className="countdown-popup-box"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="countdown-popup-close"
          onClick={onClose}
          aria-label="Fermer"
        >
          ×
        </button>
        <Countdown />
      </div>
    </div>
  );
};

export default CountdownPopup;
