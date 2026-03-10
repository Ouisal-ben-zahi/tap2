from flask import Blueprint, request, jsonify
import re
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
import random
import smtplib
import ssl
from email.message import EmailMessage

import jwt

from database.connection import DatabaseConnection
from minio_storage import get_minio_storage
from candidate_minio_path import get_candidate_minio_prefix


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _portfolio_pdf_exists(minio_storage, minio_prefix: str, candidate_uuid: str, version: str) -> bool:
  """Vérifie si au moins un PDF portfolio existe dans MinIO pour cette version (long ou one-page)."""
  if version == "one-page":
    names = [
      f"{minio_prefix}portfolio_{candidate_uuid}_one-page.pdf",
      f"{minio_prefix}portfolio_{candidate_uuid}_one-page_fr.pdf",
      f"{minio_prefix}portfolio_{candidate_uuid}_one-page_en.pdf",
    ]
  else:
    names = [
      f"{minio_prefix}portfolio_{candidate_uuid}.pdf",
      f"{minio_prefix}portfolio_{candidate_uuid}_fr.pdf",
      f"{minio_prefix}portfolio_{candidate_uuid}_en.pdf",
    ]
  for object_name in names:
    ok, _, _ = minio_storage.download_file(object_name)
    if ok:
      return True
  return False

JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "changeme"))
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_DAYS = int(os.getenv("JWT_EXPIRES_DAYS", "7"))


def _create_access_token(user_id: int, role: str, email: str) -> str:
  """Crée un JWT simple contenant l'id utilisateur et son rôle. PyJWT exige sub en string."""
  payload = {
      "sub": str(user_id),
      "role": role,
      "email": email,
      "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRES_DAYS),
      "iat": datetime.utcnow(),
  }
  return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _send_verification_email(email: str, code: str) -> None:
  """
  Envoie un code de vérification par email.
  Si la configuration SMTP n'est pas définie, logue simplement le code en console.
  """
  host = os.getenv("SMTP_HOST")
  port = int(os.getenv("SMTP_PORT", "587"))
  user = os.getenv("SMTP_USER")
  password = os.getenv("SMTP_PASSWORD")
  use_tls = (os.getenv("SMTP_USE_TLS", "true").lower() == "true")

  subject = "Votre code de vérification TAP"
  body = (
      "Bonjour,\n\n"
      f"Voici votre code de vérification : {code}\n"
      "Il est valable pendant 15 minutes.\n\n"
      "Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email.\n\n"
      "L'équipe TAP"
  )

  # Si pas de config SMTP, on logue le code pour le développement
  if not host or not user or not password:
      print(f"📧 [DEV] Code de vérification pour {email}: {code}")
      return

  try:
      msg = EmailMessage()
      msg["Subject"] = subject
      msg["From"] = user
      msg["To"] = email
      msg.set_content(body)

      context = ssl.create_default_context()
      with smtplib.SMTP(host, port) as server:
          if use_tls:
              server.starttls(context=context)
          server.login(user, password)
          server.send_message(msg)
      print(f"📧 Code de vérification envoyé à {email}")
  except Exception as e:
      # En cas d'erreur d'envoi, on ne bloque pas l'inscription mais on logue l'erreur
      print(f"❌ Erreur lors de l'envoi du code de vérification à {email}: {e}")


def _decode_token_from_request():
  """Récupère et décode le token JWT depuis l'en-tête Authorization."""
  auth_header = request.headers.get("Authorization", "")
  if not auth_header.startswith("Bearer "):
      print("🔐 [Auth] Pas d'en-tête Authorization ou format invalide")
      return None, ("Missing or invalid Authorization header", 401)

  token = auth_header.split(" ", 1)[1].strip()
  if not token:
      print("🔐 [Auth] Token vide")
      return None, ("Missing token", 401)

  try:
      payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
      sub = payload.get("sub")
      user_id = int(sub) if sub is not None else None
      payload["sub"] = user_id  # normaliser en int pour le reste du code
      print(f"🔐 [Auth] user_id reçu du token: {user_id}")
      return payload, None
  except jwt.ExpiredSignatureError:
      print("🔐 [Auth] Token expiré, user_id non disponible")
      return None, ("Token expired", 401)
  except jwt.InvalidTokenError as e:
      print(f"🔐 [Auth] Token invalide (decode failed), user_id non disponible: {e}")
      return None, ("Invalid token", 401)


def get_optional_user():
  """
  Retourne (user_id, role) si la requête contient un token JWT valide et rôle candidat,
  sinon (None, None). Utilisé par les routes qui peuvent être appelées avec ou sans auth
  (ex: /process) pour enregistrer le user_id dès la création du candidat.
  """
  payload, error = _decode_token_from_request()
  if error or not payload:
      return None, None
  user_id = payload.get("sub")
  role = (payload.get("role") or "").strip().lower()
  if role != "candidat" or not user_id:
      return None, None
  return user_id, role


def get_optional_user_from_request():
  """
  Retourne (user_id, role) pour les routes multipart (ex: /process).
  Essaie d'abord l'en-tête Authorization, puis le champ form 'auth_token' si présent.
  """
  # 1) En-tête Authorization
  payload, _ = _decode_token_from_request()
  if payload:
      user_id = payload.get("sub")
      role = (payload.get("role") or "").strip().lower()
      if role == "candidat" and user_id:
          print(f"🔐 [Auth] user_id depuis Authorization: {user_id}")
          return user_id, role
  # 2) Fallback: token dans le formulaire (multipart)
  token = (request.form.get("auth_token") or "").strip() if request.form else None
  if token:
      try:
          payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
          user_id = payload.get("sub")
          if user_id is not None:
              user_id = int(user_id)
          role = (payload.get("role") or "").strip().lower()
          if role == "candidat" and user_id:
              print(f"🔐 [Auth] user_id depuis form auth_token: {user_id}")
              return user_id, role
      except (jwt.InvalidTokenError, ValueError, TypeError):
          pass
  return None, None


@auth_bp.route("/register", methods=["POST"])
def register():
  """
  Inscription d'un utilisateur.
  Body attendu (JSON) :
  {
    "email": "user@example.com",
    "password": "motdepasse",
    "role": "candidat" | "recruteur"
  }
  """
  data = request.get_json(silent=True) or {}
  email = (data.get("email") or "").strip().lower()
  password = data.get("password") or ""
  role = (data.get("role") or "").strip().lower()

  # Validation basique du format d'email côté backend
  email_pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
  if not email or not re.match(email_pattern, email):
      return jsonify({
          "ok": False,
          "error": "INVALID_EMAIL",
          "message": "Veuillez saisir une adresse email valide"
      }), 400

  if not password or role not in ("candidat", "recruteur"):
      return jsonify({
          "ok": False,
          "error": "INVALID_INPUT",
          "message": "email, password et role ('candidat' ou 'recruteur') sont requis"
      }), 400

  password_hash = generate_password_hash(password)

  try:
      DatabaseConnection.initialize()
      with DatabaseConnection.get_connection() as conn:
          cursor = conn.cursor(dictionary=True)

          # Vérifier si l'email existe déjà
          cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
          existing = cursor.fetchone()
          if existing:
              cursor.close()
              return jsonify({
                  "ok": False,
                  "error": "EMAIL_ALREADY_EXISTS",
                  "message": "Un compte existe déjà avec cet email"
              }), 409

          cursor.execute(
              """
              INSERT INTO users (email, password_hash, role, is_verified)
              VALUES (%s, %s, %s, %s)
              """,
              (email, password_hash, role, 0),
          )
          user_id = cursor.lastrowid

          # S'assurer que la table des codes de vérification existe
          cursor.execute(
              """
              CREATE TABLE IF NOT EXISTS email_verification_tokens (
                  id INT AUTO_INCREMENT PRIMARY KEY,
                  user_id INT NOT NULL,
                  code VARCHAR(10) NOT NULL,
                  expires_at DATETIME NOT NULL,
                  used TINYINT(1) NOT NULL DEFAULT 0,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_evt_user (user_id),
                  INDEX idx_evt_code (code)
              ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
              """
          )

          # Générer et stocker un code de vérification (6 chiffres)
          code = f"{random.randint(0, 999999):06d}"
          expires_at = datetime.utcnow() + timedelta(minutes=15)
          cursor.execute(
              """
              INSERT INTO email_verification_tokens (user_id, code, expires_at, used)
              VALUES (%s, %s, %s, 0)
              """,
              (user_id, code, expires_at),
          )

          conn.commit()
          cursor.close()

      # Envoyer le code par email (ou le loguer en dev si SMTP non configuré)
      _send_verification_email(email, code)

      return jsonify({
          "ok": True,
          "requires_verification": True,
          "message": "Un code de vérification a été envoyé à votre adresse email. Veuillez le saisir pour activer votre compte."
      }), 201

  except Exception as e:
      # Ne pas exposer l'erreur SQL brute côté client
      print(f"❌ Error in /auth/register: {e}")
      return jsonify({
          "ok": False,
          "error": "SERVER_ERROR",
          "message": "Erreur serveur lors de la création du compte"
      }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
  """
  Connexion d'un utilisateur.
  Body attendu (JSON) :
  {
    "email": "user@example.com",
    "password": "motdepasse"
  }
  """
  data = request.get_json(silent=True) or {}
  email = (data.get("email") or "").strip().lower()
  password = data.get("password") or ""

  if not email or not password:
      return jsonify({
          "ok": False,
          "error": "INVALID_INPUT",
          "message": "email et password sont requis"
      }), 400

  try:
      DatabaseConnection.initialize()
      with DatabaseConnection.get_connection() as conn:
          cursor = conn.cursor(dictionary=True)
          cursor.execute(
              "SELECT id, email, password_hash, role, is_verified FROM users WHERE email = %s",
              (email,),
          )
          user = cursor.fetchone()
          cursor.close()

      if not user or not check_password_hash(user["password_hash"], password):
          return jsonify({
              "ok": False,
              "error": "INVALID_CREDENTIALS",
              "message": "Email ou mot de passe incorrect"
          }), 401
      
      # Vérifier que l'email a été validé
      if not user.get("is_verified"):
          return jsonify({
              "ok": False,
              "error": "EMAIL_NOT_VERIFIED",
              "message": "Veuillez vérifier votre email avant de vous connecter"
          }), 403

      token = _create_access_token(user["id"], user["role"], user["email"])
      return jsonify({
          "ok": True,
          "user": {
              "id": user["id"],
              "email": user["email"],
              "role": user["role"],
          },
          "token": token,
      }), 200

  except Exception as e:
      print(f"❌ Error in /auth/login: {e}")
      return jsonify({
          "ok": False,
          "error": "SERVER_ERROR",
          "message": "Erreur serveur lors de la connexion"
      }), 500


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
  """
  Vérifie un code de confirmation envoyé par email.
  Body attendu (JSON) :
  {
    "email": "user@example.com",
    "code": "123456"
  }
  """
  data = request.get_json(silent=True) or {}
  email = (data.get("email") or "").strip().lower()
  code = (data.get("code") or "").strip()

  if not email or not code:
      return jsonify({
          "ok": False,
          "error": "INVALID_INPUT",
          "message": "email et code sont requis"
      }), 400

  try:
      DatabaseConnection.initialize()
      with DatabaseConnection.get_connection() as conn:
          cursor = conn.cursor(dictionary=True)

          cursor.execute(
              "SELECT id FROM users WHERE email = %s",
              (email,),
          )
          user = cursor.fetchone()
          if not user:
              cursor.close()
              return jsonify({
                  "ok": False,
                  "error": "UNKNOWN_EMAIL",
                  "message": "Aucun compte trouvé pour cet email"
              }), 404

          user_id = user["id"]

          cursor.execute(
              """
              SELECT id, code, expires_at, used
              FROM email_verification_tokens
              WHERE user_id = %s AND code = %s
              ORDER BY id DESC
              LIMIT 1
              """,
              (user_id, code),
          )
          token_row = cursor.fetchone()

          if not token_row:
              cursor.close()
              return jsonify({
                  "ok": False,
                  "error": "INVALID_CODE",
                  "message": "Code de vérification invalide"
              }), 400

          if token_row["used"]:
              cursor.close()
              return jsonify({
                  "ok": False,
                  "error": "CODE_ALREADY_USED",
                  "message": "Ce code a déjà été utilisé"
              }), 400

          expires_at = token_row["expires_at"]
          if isinstance(expires_at, datetime) and expires_at <= datetime.utcnow():
              cursor.close()
              return jsonify({
                  "ok": False,
                  "error": "CODE_EXPIRED",
                  "message": "Ce code de vérification a expiré"
              }), 400

          # Marquer le code comme utilisé
          cursor.execute(
              "UPDATE email_verification_tokens SET used = 1 WHERE id = %s",
              (token_row["id"],),
          )

          # Marquer l'utilisateur comme vérifié
          cursor.execute(
              "UPDATE users SET is_verified = 1 WHERE id = %s",
              (user_id,),
          )

          conn.commit()
          cursor.close()

      return jsonify({
          "ok": True,
          "message": "Votre email a été vérifié. Vous pouvez maintenant vous connecter."
      }), 200

  except Exception as e:
      print(f"❌ Error in /auth/verify-email: {e}")
      return jsonify({
          "ok": False,
          "error": "SERVER_ERROR",
          "message": "Erreur serveur lors de la vérification de l'email"
      }), 500


@auth_bp.route("/me", methods=["GET"])
def me():
  """
  Retourne les informations de l'utilisateur courant à partir du token JWT.
  Header attendu :
    Authorization: Bearer <token>
  """
  payload, error = _decode_token_from_request()
  if error:
      message, status_code = error
      return jsonify({
          "ok": False,
          "error": "UNAUTHORIZED",
          "message": message,
      }), status_code

  user_id = payload.get("sub")
  role = payload.get("role")
  email = payload.get("email")

  if not user_id or not role or not email:
      return jsonify({
          "ok": False,
          "error": "INVALID_TOKEN",
          "message": "Token invalide"
      }), 401

  return jsonify({
      "ok": True,
      "user": {
          "id": user_id,
          "email": email,
          "role": role,
      }
  }), 200


@auth_bp.route("/me/candidate/progress", methods=["GET"])
def candidate_progress():
  """
  Retourne la progression du candidat connecté (étape atteinte + IDs).
  Utilise l'email du user pour retrouver le dernier candidat créé avec cet email.
  """
  payload, error = _decode_token_from_request()
  if error:
      message, status_code = error
      return jsonify({
          "ok": False,
          "error": "UNAUTHORIZED",
          "message": message,
      }), status_code

  user_id = payload.get("sub")
  role = payload.get("role")
  email = (payload.get("email") or "").strip().lower()

  if role != "candidat" or not user_id:
      return jsonify({
          "ok": False,
          "error": "FORBIDDEN",
          "message": "Seuls les comptes candidats peuvent accéder à cette ressource"
      }), 403

  try:
      DatabaseConnection.initialize()
      with DatabaseConnection.get_connection() as conn:
          cursor = conn.cursor(dictionary=True)

          # 1) Récupérer le dernier candidat lié à ce user_id (colonne user_id)
          cursor.execute(
              """
              SELECT id, candidate_uuid, id_agent
              FROM candidates
              WHERE user_id = %s
              ORDER BY id DESC
              LIMIT 1
              """,
              (user_id,),
          )
          candidate = cursor.fetchone()

          # Si aucun candidat lié, chercher par email et lier le compte (candidats créés avant connexion)
          if not candidate and email:
              cursor.execute(
                  """
                  SELECT id, candidate_uuid, id_agent
                  FROM candidates
                  WHERE LOWER(TRIM(email)) = %s
                  ORDER BY id DESC
                  LIMIT 1
                  """,
                  (email,),
              )
              candidate = cursor.fetchone()
              if candidate:
                  cursor.execute(
                      "UPDATE candidates SET user_id = %s WHERE id = %s",
                      (user_id, candidate["id"]),
                  )
                  conn.commit()

          if not candidate:
              cursor.close()
              return jsonify({
                  "ok": True,
                  "candidate": None,
                  "max_step": 1
              }), 200

          db_candidate_id = candidate["id"]
          candidate_uuid = candidate.get("candidate_uuid") or candidate.get("id_agent") or str(db_candidate_id)

          # Vérifier s'il existe au moins une version de CV corrigé pour ce candidat
          cursor.execute(
              """
              SELECT 1
              FROM corrected_cv_versions
              WHERE candidate_id = %s
              LIMIT 1
              """,
              (db_candidate_id,),
          )
          has_corrected_cv = cursor.fetchone() is not None

          cursor.close()

      has_talentcard = True  # existence de la ligne candidates

      # Mapper sur ton système d'étapes (RequireStep)
      # 1 : rien, 4 : Talent Card ok, 6 : CV corrigé ok
      if has_corrected_cv:
          max_step = 6
      elif has_talentcard:
          max_step = 4
      else:
          max_step = 1

      return jsonify({
          "ok": True,
          "candidate": {
              "db_candidate_id": db_candidate_id,
              "candidate_id": candidate_uuid,
              "has_talentcard": has_talentcard,
              "has_corrected_cv": has_corrected_cv,
          },
          "max_step": max_step,
      }), 200

  except Exception as e:
      print(f"❌ Error in /auth/me/candidate/progress: {e}")
      print(f"❌ User ID: {user_id}")
      print(f"❌ Email: {email}")
      print(f"❌ Role: {role}")
      print(f"❌ Error in /auth/me/candidate/progress: {e}")
      return jsonify({
          "ok": False,
          "error": "SERVER_ERROR",
          "message": "Erreur serveur lors de la récupération de la progression"
      }), 500


@auth_bp.route("/me/files", methods=["GET"])
def my_generated_files():
  """
  Retourne la liste des fichiers générés pour le candidat connecté
  (Talent Card, CV corrigé, Portfolio long, Portfolio one-page).
  """
  payload, error = _decode_token_from_request()
  if error:
      message, status_code = error
      return jsonify({
          "ok": False,
          "error": "UNAUTHORIZED",
          "message": message,
      }), status_code

  user_id = payload.get("sub")
  role = payload.get("role")

  if role != "candidat" or not user_id:
      return jsonify({
          "ok": False,
          "error": "FORBIDDEN",
          "message": "Seuls les comptes candidats peuvent accéder à cette ressource"
      }), 403

  email = (payload.get("email") or "").strip().lower()
  try:
      DatabaseConnection.initialize()
      with DatabaseConnection.get_connection() as conn:
          cursor = conn.cursor(dictionary=True)
          cursor.execute(
              """
              SELECT id, candidate_uuid, nom, prenom, talentcard_pdf_minio_url
              FROM candidates
              WHERE user_id = %s
              ORDER BY id DESC
              LIMIT 1
              """,
              (user_id,),
          )
          candidate = cursor.fetchone()

          # Si aucun candidat lié au user_id, chercher par email (candidats créés avant connexion)
          if not candidate and email:
              cursor.execute(
                  """
                  SELECT id, candidate_uuid, nom, prenom, talentcard_pdf_minio_url
                  FROM candidates
                  WHERE LOWER(TRIM(email)) = %s
                  ORDER BY id DESC
                  LIMIT 1
                  """,
                  (email,),
              )
              candidate = cursor.fetchone()
              if candidate:
                  cursor.execute(
                      "UPDATE candidates SET user_id = %s WHERE id = %s",
                      (user_id, candidate["id"]),
                  )
                  conn.commit()

          if not candidate:
              cursor.close()
              return jsonify({
                  "ok": True,
                  "candidate": None,
                  "files": []
              }), 200

          db_candidate_id = candidate["id"]
          candidate_uuid = candidate.get("candidate_uuid") or str(candidate["id"])
          nom = candidate.get("nom") or ""
          prenom = candidate.get("prenom") or ""
          has_talentcard_pdf = bool(candidate.get("talentcard_pdf_minio_url"))

          cursor.execute(
              """
              SELECT 1 FROM corrected_cv_versions
              WHERE candidate_id = %s LIMIT 1
              """,
              (db_candidate_id,),
          )
          has_corrected_cv = cursor.fetchone() is not None
          cursor.close()

      # Vérifier si les PDF portfolio existent dans MinIO
      has_portfolio_long = False
      has_portfolio_one_page = False
      try:
        minio_storage = get_minio_storage()
        if minio_storage and minio_storage.client:
          minio_prefix = get_candidate_minio_prefix(db_candidate_id)
          has_portfolio_long = _portfolio_pdf_exists(
            minio_storage, minio_prefix, candidate_uuid, "long"
          )
          has_portfolio_one_page = _portfolio_pdf_exists(
            minio_storage, minio_prefix, candidate_uuid, "one-page"
          )
      except Exception as e:
        print(f"⚠️ [Auth] Vérification portfolio MinIO: {e}")

      # max_step pour que le front redirige vers la bonne étape (1, 4, 6, etc.)
      has_talentcard = has_talentcard_pdf
      if has_corrected_cv:
        max_step = 6
      elif has_talentcard:
        max_step = 4
      else:
        max_step = 1

      # URLs relatives pour que le front puisse les préfixer avec API_URL
      base = os.getenv("RECRUIT_BASE_URL") or ""  # vide = chemins relatifs
      if not base and hasattr(request, "url_root"):
          base = (request.url_root or "").rstrip("/")
      prefix = base.rstrip("/") if base else ""

      def url(path):
          return f"{prefix}{path}" if prefix else path

      files = []

      if has_talentcard_pdf:
          files.append({
              "type": "talent_card",
              "label": "Talent Card (PDF)",
              "previewUrl": url(f"/talentcard/{db_candidate_id}/preview"),
              "downloadUrl": url(f"/talentcard/{db_candidate_id}/download"),
              "available": True,
          })
      else:
          files.append({
              "type": "talent_card",
              "label": "Talent Card (PDF)",
              "previewUrl": url(f"/talentcard/{db_candidate_id}/preview"),
              "downloadUrl": url(f"/talentcard/{db_candidate_id}/download"),
              "available": False,
          })

      files.append({
          "type": "cv",
          "label": "CV corrigé (PDF)",
          "previewUrl": url(f"/correctedcv/{candidate_uuid}/preview?db_candidate_id={db_candidate_id}"),
          "downloadUrl": url(f"/correctedcv/{candidate_uuid}/download?db_candidate_id={db_candidate_id}"),
          "available": has_corrected_cv,
      })

      files.append({
          "type": "portfolio_long",
          "label": "Portfolio (version longue)",
          "previewUrl": url(f"/portfolio/{candidate_uuid}/pdf?db_candidate_id={db_candidate_id}&version=long"),
          "downloadUrl": url(f"/portfolio/{candidate_uuid}/pdf?db_candidate_id={db_candidate_id}&version=long&download=1"),
          "available": has_portfolio_long,
      })

      files.append({
          "type": "portfolio_one_page",
          "label": "Portfolio (one-page)",
          "previewUrl": url(f"/portfolio/{candidate_uuid}/pdf?db_candidate_id={db_candidate_id}&version=one-page"),
          "downloadUrl": url(f"/portfolio/{candidate_uuid}/pdf?db_candidate_id={db_candidate_id}&version=one-page&download=1"),
          "available": has_portfolio_one_page,
      })

      return jsonify({
          "ok": True,
          "candidate": {
              "db_candidate_id": db_candidate_id,
              "candidate_uuid": candidate_uuid,
              "nom": nom,
              "prenom": prenom,
          },
          "max_step": max_step,
          "files": files,
      }), 200

  except Exception as e:
      print(f"❌ Error in /auth/me/files: {e}")
      return jsonify({
          "ok": False,
          "error": "SERVER_ERROR",
          "message": "Erreur serveur lors de la récupération des fichiers",
      }), 500









from flask import Blueprint, request, jsonify, redirect
import os
import json
import secrets
import base64
import hmac
import hashlib
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

oauth_bp = Blueprint("oauth", __name__, url_prefix="/api/auth")

ALLOWED_PROVIDERS = {"google", "github", "linkedin"}
ALLOWED_USER_TYPES = {"candidate", "recruiter"}
ALLOWED_INTENTS = {"signup", "login"}
ALLOWED_RETURN_PATHS = {
    "/",
    "/signup",
    "/recruteur",
    "/signup/candidat",
    "/signup/recruteur",
    "/mes-fichiers",
}


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _default_return_path(user_type: str, intent: str) -> str:
    if user_type == "recruiter":
        return "/recruteur" if intent == "login" else "/signup/recruteur"
    return "/" if intent == "login" else "/signup/candidat"


def _sanitize_return_path(path: str | None, user_type: str, intent: str) -> str:
    p = (path or "").strip()
    if p in ALLOWED_RETURN_PATHS:
        return p
    return _default_return_path(user_type, intent)


def _state_secret() -> bytes:
    return _env("JWT_SECRET", "change-me").encode("utf-8")


def _encode_state(payload: dict) -> str:
    envelope = dict(payload)
    envelope["exp"] = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
    envelope["nonce"] = secrets.token_urlsafe(12)
    raw = json.dumps(envelope, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    raw_b64 = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(_state_secret(), raw_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{raw_b64}.{sig}"


def _decode_state(token: str) -> dict | None:
    if not token or "." not in token:
        return None
    try:
        raw_b64, sig = token.rsplit(".", 1)
        expected = hmac.new(_state_secret(), raw_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        padded = raw_b64 + "=" * ((4 - len(raw_b64) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.utcnow().timestamp()):
            return None
        return payload
    except Exception:
        return None


def _encode_session_payload(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _frontend_base_url() -> str:
    return (_env("OAUTH_FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")


def _redirect_uri(provider: str) -> str:
    specific = _env(f"OAUTH_{provider.upper()}_REDIRECT_URI")
    if specific:
        return specific
    return f"{request.url_root.rstrip('/')}/api/auth/oauth/{provider}/callback"


def _credentials(provider: str) -> tuple[str, str]:
    p = provider.upper()
    client_id = _env(f"OAUTH_{p}_CLIENT_ID")
    client_secret = _env(f"OAUTH_{p}_CLIENT_SECRET")
    return client_id, client_secret


def _authorize_url(provider: str, state_token: str) -> tuple[bool, str]:
    client_id, _ = _credentials(provider)
    if not client_id:
        return False, "OAuth client_id missing"

    redirect_uri = _redirect_uri(provider)

    if provider == "google":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state_token,
            "prompt": "select_account",
        }
        return True, f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    if provider == "github":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state_token,
        }
        return True, f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    if provider == "linkedin":
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state_token,
        }
        return True, f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"

    return False, "Unsupported provider"


def _http_error_message(resp: requests.Response, fallback: str) -> str:
    try:
        data = resp.json()
        return data.get("error_description") or data.get("error") or data.get("message") or fallback
    except Exception:
        return fallback


def _exchange_code(provider: str, code: str, redirect_uri: str) -> tuple[bool, str]:
    client_id, client_secret = _credentials(provider)
    if not client_id or not client_secret:
        return False, f"Missing OAuth credentials for {provider}"

    try:
        if provider == "google":
            resp = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=20,
            )
        elif provider == "github":
            resp = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                timeout=20,
            )
        elif provider == "linkedin":
            resp = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=20,
            )
        else:
            return False, "Unsupported provider"

        if resp.status_code >= 400:
            return False, _http_error_message(resp, "OAuth token exchange failed")

        data = resp.json()
        token = data.get("access_token")
        if not token:
            return False, "No access_token in OAuth response"
        return True, token
    except Exception as exc:
        return False, f"OAuth exchange failed: {exc}"


def _split_name(full_name: str) -> tuple[str, str]:
    n = (full_name or "").strip()
    if not n:
        return "", ""
    parts = n.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _fetch_profile(provider: str, access_token: str) -> tuple[bool, dict | str]:
    try:
        if provider == "google":
            resp = requests.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
            )
            if resp.status_code >= 400:
                return False, _http_error_message(resp, "Cannot fetch Google profile")
            data = resp.json()
            first_name = (data.get("given_name") or "").strip()
            last_name = (data.get("family_name") or "").strip()
            full_name = (data.get("name") or "").strip()
            if not (first_name or last_name):
                first_name, last_name = _split_name(full_name)
            profile_url = (data.get("profile") or "").strip() or None
            if not profile_url and data.get("sub"):
                profile_url = f"https://profiles.google.com/{data.get('sub')}"
            return True, {
                "provider": "google",
                "email": (data.get("email") or "").strip().lower(),
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name or f"{first_name} {last_name}".strip(),
                "profile_url": profile_url,
                "provider_user_id": str(data.get("sub") or ""),
                "username": "",
                "avatar_url": (data.get("picture") or "").strip() or None,
            }

        if provider == "linkedin":
            resp = requests.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
            )
            if resp.status_code >= 400:
                return False, _http_error_message(resp, "Cannot fetch LinkedIn profile")
            data = resp.json()
            first_name = (data.get("given_name") or "").strip()
            last_name = (data.get("family_name") or "").strip()
            full_name = (data.get("name") or "").strip()
            if not (first_name or last_name):
                first_name, last_name = _split_name(full_name)
            profile_url = (data.get("profile") or "").strip() or None
            provider_user_id = str(data.get("sub") or "")
            if not profile_url and provider_user_id:
                profile_url = f"https://www.linkedin.com/in/{provider_user_id}"
            return True, {
                "provider": "linkedin",
                "email": (data.get("email") or "").strip().lower(),
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name or f"{first_name} {last_name}".strip(),
                "profile_url": profile_url,
                "provider_user_id": provider_user_id,
                "username": "",
                "avatar_url": (data.get("picture") or "").strip() or None,
            }

        if provider == "github":
            user_resp = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=20,
            )
            if user_resp.status_code >= 400:
                return False, _http_error_message(user_resp, "Cannot fetch GitHub profile")

            user_data = user_resp.json()
            email = (user_data.get("email") or "").strip().lower()
            if not email:
                emails_resp = requests.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=20,
                )
                if emails_resp.status_code < 400:
                    emails = emails_resp.json() or []
                    primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                    fallback = next((e for e in emails if e.get("verified")), None) or (emails[0] if emails else None)
                    email = ((primary or fallback or {}).get("email") or "").strip().lower()

            full_name = (user_data.get("name") or "").strip()
            username = (user_data.get("login") or "").strip()
            first_name, last_name = _split_name(full_name or username)
            profile_url = (user_data.get("html_url") or "").strip() or None
            if not profile_url and username:
                profile_url = f"https://github.com/{username}"

            return True, {
                "provider": "github",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name or username,
                "profile_url": profile_url,
                "provider_user_id": str(user_data.get("id") or ""),
                "username": username,
                "avatar_url": (user_data.get("avatar_url") or "").strip() or None,
            }

        return False, "Unsupported provider"
    except Exception as exc:
        return False, f"Profile fetch failed: {exc}"


def _oauth_error_redirect(return_path: str, message: str):
    fragment = urlencode({"oauth_error": (message or "OAuth error").strip()})
    return redirect(f"{_frontend_base_url()}{return_path}#{fragment}")


def issue_app_session(profile: dict, context: dict) -> tuple[bool, dict | str]:
    """
    Crée / retrouve un utilisateur applicatif à partir du profil OAuth
    puis retourne une "session" pour le front.
    """
    email = (profile.get("email") or "").strip().lower()
    if not email:
        return False, "Le fournisseur OAuth n'a pas renvoyé d'email vérifié"

    provider = (profile.get("provider") or "").strip().lower()
    user_type = (context.get("user_type") or "candidate").strip().lower()
    intent = (context.get("intent") or "signup").strip().lower()

    # Mapping user_type (côté OAuth) -> role (colonne dans la table users)
    role = "candidat" if user_type == "candidate" else "recruteur"

    try:
        DatabaseConnection.initialize()
        with DatabaseConnection.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, email, role FROM users WHERE email = %s",
                (email,),
            )
            user = cursor.fetchone()

            created = False

            if not user:
                if intent == "login":
                    cursor.close()
                    return False, "Aucun compte trouvé pour cet email"

                # Création d'un utilisateur sans mot de passe explicite
                # (il se connectera uniquement via OAuth)
                random_password = secrets.token_urlsafe(32)
                password_hash = generate_password_hash(random_password)

                cursor.execute(
                    """
                    INSERT INTO users (email, password_hash, role, is_verified)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (email, password_hash, role, 1),
                )
                user_id = cursor.lastrowid
                conn.commit()
                created = True
                cursor.close()
            else:
                user_id = user["id"]
                cursor.close()

        token = _create_access_token(user_id, role, email)
        expires_at = int((datetime.utcnow() + timedelta(days=JWT_EXPIRES_DAYS)).timestamp())

        session_payload = {
            "token": token,
            "expires_at": expires_at,
            "user_type": user_type,
            "user": {
                "id": user_id,
                "email": email,
                "role": role,
                "first_name": profile.get("first_name") or "",
                "last_name": profile.get("last_name") or "",
                "full_name": profile.get("full_name") or "",
                "avatar_url": profile.get("avatar_url"),
                "provider": provider,
                "provider_user_id": profile.get("provider_user_id"),
                "username": profile.get("username") or "",
                "profile_url": profile.get("profile_url"),
                "created_via_oauth": created,
            },
        }

        return True, session_payload

    except Exception as e:
        print(f"❌ Error in issue_app_session: {e}")
        return False, "Erreur serveur lors de la connexion OAuth"


@oauth_bp.route("/oauth/<provider>/start", methods=["GET"])
def oauth_start(provider):
    provider = (provider or "").strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        return jsonify({"error": "Unsupported provider"}), 400

    user_type = (request.args.get("user_type") or "candidate").strip().lower()
    intent = (request.args.get("intent") or "signup").strip().lower()
    if user_type not in ALLOWED_USER_TYPES:
        return jsonify({"error": "Invalid user_type"}), 400
    if intent not in ALLOWED_INTENTS:
        return jsonify({"error": "Invalid intent"}), 400

    return_path = _sanitize_return_path(request.args.get("return_path"), user_type, intent)
    client_id, client_secret = _credentials(provider)
    if not client_id or not client_secret:
        p = provider.upper()
        return jsonify({
            "error": f"Missing OAuth config for {provider}. Expected OAUTH_{p}_CLIENT_ID and OAUTH_{p}_CLIENT_SECRET"
        }), 500

    state_token = _encode_state({
        "provider": provider,
        "user_type": user_type,
        "intent": intent,
        "return_path": return_path,
    })
    ok, url_or_error = _authorize_url(provider, state_token)
    if not ok:
        return jsonify({"error": url_or_error}), 500
    return redirect(url_or_error, code=302)


@oauth_bp.route("/oauth/<provider>/callback", methods=["GET"])
def oauth_callback(provider):
    provider = (provider or "").strip().lower()
    if provider not in ALLOWED_PROVIDERS:
        return jsonify({"error": "Unsupported provider"}), 400

    decoded_state = _decode_state(request.args.get("state") or "")
    fallback_path = "/signup"
    if decoded_state:
        fallback_path = _sanitize_return_path(
            decoded_state.get("return_path"),
            decoded_state.get("user_type", "candidate"),
            decoded_state.get("intent", "signup"),
        )

    provider_error = request.args.get("error_description") or request.args.get("error")
    if provider_error:
        return _oauth_error_redirect(fallback_path, provider_error)

    if not decoded_state:
        return _oauth_error_redirect(fallback_path, "Invalid or expired OAuth state")

    if decoded_state.get("provider") != provider:
        return _oauth_error_redirect(fallback_path, "OAuth provider mismatch")

    code = request.args.get("code")
    if not code:
        return _oauth_error_redirect(fallback_path, "OAuth code missing")

    ok, token_or_error = _exchange_code(provider, code, _redirect_uri(provider))
    if not ok:
        return _oauth_error_redirect(fallback_path, token_or_error)

    ok, profile_or_error = _fetch_profile(provider, token_or_error)
    if not ok:
        return _oauth_error_redirect(fallback_path, profile_or_error)

    auth_ok, session_or_error = issue_app_session(profile_or_error, decoded_state)
    if not auth_ok:
        return _oauth_error_redirect(fallback_path, str(session_or_error))

    oauth_session = _encode_session_payload(session_or_error)
    return redirect(f"{_frontend_base_url()}{fallback_path}#oauth_session={oauth_session}", code=302)
