#!/usr/bin/env python3
import os
import time
from typing import List, Dict

from TTS.api import TTS
import simpleaudio as sa
from dotenv import load_dotenv

load_dotenv()
# Si vous utilisez openai>=1.0.0
USE_OPENAI = bool(os.getenv("OPEN_AI_API"))
if USE_OPENAI:
    # nouvelle interface openai
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPEN_AI_API"))

# Initialisation TTS (modèle français)
tts = TTS(model_name="tts_models/fr/css10/vits", progress_bar=False, gpu=False)
OUTPUT_WAV = "output.wav"

# Conversation history (pour contexte)
SYSTEM_PROMPT = "Tu es un assistant conversationnel en français, poli et utile. Répond de façon concise et humaine."
MAX_HISTORY_MESSAGES = 10  # limiter la mémoire pour éviter les prompts trop longs

def sanitize_for_tts(text: str) -> str:
    """Nettoie le texte pour éviter les caractères non supportés par le modèle TTS."""
    # remplacer les guillemets français, NBSP, etc.
    text = text.replace("«", '"').replace("»", '"')
    text = text.replace("\u00A0", " ")  # non-breaking space
    # optionnel: d'autres nettoyages (supprimer caractères non imprimables)
    text = "".join(ch for ch in text if ord(ch) >= 9)
    return text

def synthesize_and_play(text: str):
    """Génère un WAV via TTS et joue le son."""
    safe_text = sanitize_for_tts(text)
    try:
        tts.tts_to_file(text=safe_text, file_path=OUTPUT_WAV)
    except Exception as e:
        print(f"[Erreur TTS génération] {e}")
        return
    try:
        wave_obj = sa.WaveObject.from_wave_file(OUTPUT_WAV)
        play_obj = wave_obj.play()
        play_obj.wait_done()
    except Exception as e:
        print(f"[Erreur lecture audio] {e}")

def simple_keyword_response(user_text: str) -> str:
    """Fallback simple basé sur mots-clés pour donner une réponse utile sans OpenAI."""
    low = user_text.lower()
    if any(word in low for word in ("stress", "stresser", "stresse", "anguoisse", "anxi")) and any(word in low for word in ("entretien", "interview", "entretien d'embauche", "job")):
        return (
            "Voici quelques conseils pour réduire le stress avant un entretien : "
            "1) Préparez vos réponses aux questions classiques et répétez-les à voix haute, "
            "2) Faites des exercices de respiration profonde juste avant l'entretien, "
            "3) Informez-vous sur l'entreprise pour vous sentir plus confiant, "
            "4) Arrivez en avance et organisez vos documents, "
            "5) Rappelez-vous que l'entretien est un échange : vous évaluez aussi l'entreprise."
        )
    if any(word in low for word in ("bonjour", "salut", "coucou")):
        return "Bonjour ! Comment puis-je vous aider aujourd'hui ?"
    # fallback générique plus naturel que "Peux-tu préciser ?"
    return "Désolé, je n'ai pas pu contacter le service de génération. Peux-tu préciser ta demande ou poser une question plus ciblée ?"

def get_bot_response(history: List[Dict[str, str]], user_message: str) -> str:
    """Retourne la réponse du bot en utilisant OpenAI si disponible, sinon fallback."""
    # Ajout du message utilisateur à l'historique local (ne pas muter l'original si nécessaire)
    history.append({"role": "user", "content": user_message})
    # Garder seulement les derniers messages utiles (system + derniers échanges)
    # Construire la liste messages pour l'API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Prendre jusqu'à MAX_HISTORY_MESSAGES des derniers échanges (user/assistant)
    trimmed = history[-MAX_HISTORY_MESSAGES:]
    messages.extend(trimmed)

    if USE_OPENAI:
        try:
            resp = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=400,
                temperature=0.8,
            )
            # Extraire le texte de la réponse
            assistant_content = resp.choices[0].message.get("content", "").strip()
            # Ajouter la réponse au history
            history.append({"role": "assistant", "content": assistant_content})
            return assistant_content
        except Exception as e:
            # Afficher l'erreur et tomber en fallback
            print(f"[Erreur OpenAI] {e}")

    # Si OpenAI non configuré ou erreur -> fallback basé sur mots-clés
    assistant_content = simple_keyword_response(user_message)
    history.append({"role": "assistant", "content": assistant_content})
    return assistant_content

def main():
    print("Conversation TTS interactive (FR). Tapez 'quit' pour quitter.")
    history: List[Dict[str, str]] = []
    while True:
        try:
            user = input("\nVous: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir.")
            break
        if not user:
            continue
        if user.lower() in ("quit", "exit", "q"):
            print("Fin de la conversation. Au revoir.")
            break

        response = get_bot_response(history, user)
        print("\nProgramme:", response)
        synthesize_and_play(response)
        # petit délai pour éviter chevauchement
        time.sleep(0.15)

if __name__ == "__main__":
    main()