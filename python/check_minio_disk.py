#!/usr/bin/env python3
"""
Script pour diagnostiquer les problèmes de stockage MinIO.
Vérifie l'espace disque et les fichiers dans MinIO.
"""

import os
import shutil
from minio_storage import get_minio_storage

def check_disk_space(path="/"):
    """Vérifie l'espace disque disponible."""
    try:
        stat = shutil.disk_usage(path)
        total_gb = stat.total / (1024**3)
        used_gb = stat.used / (1024**3)
        free_gb = stat.free / (1024**3)
        percent_used = (stat.used / stat.total) * 100
        
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent_used": round(percent_used, 2)
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    """Fonction principale."""
    print("=" * 60)
    print("🔍 DIAGNOSTIC MINIO - Vérification de l'espace disque")
    print("=" * 60)
    
    # Vérifier l'espace disque local
    print("\n📊 Espace disque du serveur (où MinIO est installé):")
    disk_info = check_disk_space("/")
    if "error" in disk_info:
        print(f"   ❌ Erreur: {disk_info['error']}")
    else:
        print(f"   Total: {disk_info['total_gb']} GB")
        print(f"   Utilisé: {disk_info['used_gb']} GB ({disk_info['percent_used']}%)")
        print(f"   Libre: {disk_info['free_gb']} GB")
        
        if disk_info['percent_used'] > 90:
            print(f"   ⚠️  ATTENTION: Disque presque plein ({disk_info['percent_used']}%)!")
        elif disk_info['percent_used'] > 80:
            print(f"   ⚠️  Attention: Disque à {disk_info['percent_used']}% de capacité")
        else:
            print(f"   ✅ Espace disque OK")
    
    # Vérifier MinIO
    print("\n📦 Informations MinIO:")
    minio_storage = get_minio_storage()
    
    if not minio_storage.client:
        print("   ❌ Impossible de se connecter à MinIO")
        return
    
    info = minio_storage.get_storage_info()
    if "error" in info:
        print(f"   ❌ Erreur: {info['error']}")
    else:
        print(f"   Total fichiers: {info['total_files']}")
        print(f"   Taille totale: {info['total_size_mb']} MB ({info['total_size_gb']} GB)")
    
    # Liste des fichiers
    print("\n📁 Fichiers dans MinIO (10 premiers):")
    files = minio_storage.list_files()
    if not files:
        print("   Aucun fichier")
    else:
        for i, obj in enumerate(files[:10], 1):
            size_mb = round(obj.size / (1024 * 1024), 2)
            print(f"   {i}. {obj.object_name} ({size_mb} MB)")
        if len(files) > 10:
            print(f"   ... et {len(files) - 10} autres fichiers")
    
    # Diagnostic
    print("\n" + "=" * 60)
    print("🔍 DIAGNOSTIC:")
    print("=" * 60)
    
    if "error" not in disk_info:
        if disk_info['percent_used'] > 90:
            print("❌ PROBLÈME IDENTIFIÉ: Le disque du serveur est presque plein!")
            print("   → C'est la cause du problème 'XMinioStorageFull'")
            print("   → MinIO refuse les uploads car le disque est plein")
            print("\n💡 SOLUTIONS:")
            print("   1. Libérez de l'espace sur le disque du serveur")
            print("   2. Supprimez des fichiers temporaires ou logs")
            print("   3. Déplacez des données vers un autre disque")
            print("   4. Augmentez la taille du disque si possible")
        elif info.get('total_files', 0) == 0 and disk_info['percent_used'] < 80:
            print("✅ MinIO est vide mais le disque a de l'espace")
            print("   → Le problème peut venir de la configuration MinIO")
            print("   → Vérifiez les logs MinIO pour plus de détails")
        else:
            print("✅ Espace disque OK, MinIO fonctionne normalement")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
