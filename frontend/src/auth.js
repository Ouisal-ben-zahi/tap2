// Utilitaires simples pour gérer le JWT côté frontend

// Récupère le payload décodé du token (ou null)
export function decodeJwt(token) {
  try {
    const [, payloadPart] = token.split(".");
    if (!payloadPart) return null;
    const json = atob(payloadPart.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

// Enregistre le token et l'état auth dans sessionStorage
export function setAuthSession(accessToken, extra = {}) {
  if (!accessToken) return;
  const payload = decodeJwt(accessToken);
  if (!payload || !payload.exp) return;

  const expMs = payload.exp * 1000;

  sessionStorage.setItem("auth", "1");
  sessionStorage.setItem("accessToken", accessToken);
  sessionStorage.setItem("accessTokenExp", String(expMs));

  if (extra.role) sessionStorage.setItem("profileType", extra.role);
  if (extra.email) sessionStorage.setItem("userEmail", extra.email);
  if (extra.id) sessionStorage.setItem("userId", String(extra.id));
}

// Vérifie si le token est encore valide (avec une petite marge)
export function isAccessTokenValid() {
  const expStr = sessionStorage.getItem("accessTokenExp");
  if (!expStr) return false;
  const expMs = Number(expStr);
  const nowMs = Date.now();
  const marginMs = 30 * 1000; // 30s de marge
  return nowMs + marginMs < expMs;
}

// Déconnecte l'utilisateur côté frontend
export function clearAuthSession() {
  sessionStorage.setItem("auth", "0");
  sessionStorage.removeItem("accessToken");
  sessionStorage.removeItem("accessTokenExp");
  sessionStorage.removeItem("authToken");
  // on laisse éventuellement profileType / userEmail selon ton besoin
}

