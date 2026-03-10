#!/usr/bin/env python3
"""
Script utilitaire pour nettoyer le stockage MinIO.
Permet de lister les fichiers et supprimer les anciens fichiers.
"""

import sys
from minio_storage import get_minio_storage

def main():
    """Fonction principale."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cleanup_minio.py info                    # Affiche les infos de stockage")
        print("  python cleanup_minio.py list [prefix]          # Liste les fichiers")
        print("  python cleanup_minio.py cleanup [days] [prefix] # Supprime les fichiers > X jours")
        print("  python cleanup_minio.py cleanup 0              # Supprime TOUS les fichiers (attention!)")
        print("  python cleanup_minio.py delete-all [prefix]    # Supprime TOUS les fichiers (avec confirmation)")
        print("  python cleanup_minio.py cleanup 30 candidates/  # Exemple: supprime fichiers > 30 jours dans candidates/")
        return
    
    command = sys.argv[1]
    minio_storage = get_minio_storage()
    
    if not minio_storage.client:
        print("❌ Impossible de se connecter à MinIO")
        return
    
    if command == "info":
        info = minio_storage.get_storage_info()
        if "error" in info:
            print(f"❌ Erreur: {info['error']}")
        else:
            print("\n📊 Informations sur le stockage MinIO:")
            print(f"   Total fichiers: {info['total_files']}")
            print(f"   Taille totale: {info['total_size_mb']} MB ({info['total_size_gb']} GB)")
    
    elif command == "list":
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        print(f"\n📁 Liste des fichiers (préfixe: '{prefix}'):")
        files = minio_storage.list_files(prefix=prefix)
        if not files:
            print("   Aucun fichier trouvé")
        else:
            for obj in files[:50]:  # Limiter à 50 pour l'affichage
                size_mb = round(obj.size / (1024 * 1024), 2)
                print(f"   {obj.object_name} ({size_mb} MB) - {obj.last_modified}")
            if len(files) > 50:
                print(f"   ... et {len(files) - 50} autres fichiers")
    
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        prefix = sys.argv[3] if len(sys.argv) > 3 else ""
        
        from datetime import datetime, timedelta, timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        print(f"\n🧹 Nettoyage des fichiers plus anciens que {days} jours...")
        print(f"   Date de coupure: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if prefix:
            print(f"   Préfixe: {prefix}")
        
        deleted_count, errors = minio_storage.cleanup_old_files(prefix=prefix, days_old=days)
        
        if deleted_count == 0:
            print(f"   ℹ️  Aucun fichier plus ancien que {days} jours trouvé.")
        
        if errors:
            print(f"\n⚠️  {len(errors)} erreur(s) lors du nettoyage:")
            for error in errors[:10]:  # Limiter l'affichage
                print(f"   {error}")
    
    elif command == "delete-all":
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        
        print(f"\n⚠️  ATTENTION: Vous allez supprimer TOUS les fichiers")
        if prefix:
            print(f"   Préfixe: {prefix}")
        else:
            print(f"   (sans préfixe = TOUS les fichiers du bucket)")
        
        response = input("   Confirmez en tapant 'OUI' (en majuscules): ")
        if response != "OUI":
            print("❌ Suppression annulée")
            return
        
        # Supprimer tous les fichiers (jours = 0)
        deleted_count, errors = minio_storage.cleanup_old_files(prefix=prefix, days_old=0)
        
        if errors:
            print(f"\n⚠️  {len(errors)} erreur(s) lors du nettoyage:")
            for error in errors[:10]:  # Limiter l'affichage
                print(f"   {error}")
    
    else:
        print(f"❌ Commande inconnue: {command}")

if __name__ == "__main__":
    main()
