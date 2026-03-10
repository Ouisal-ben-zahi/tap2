#!/usr/bin/env python3
"""
Script pour trouver les fichiers et dossiers les plus volumineux.
Aide à identifier ce qui prend de l'espace disque.
"""

import os
import sys
from pathlib import Path

def get_size(path):
    """Calcule la taille d'un fichier ou dossier."""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        elif os.path.isdir(path):
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
            return total
    except (OSError, PermissionError):
        return 0
    return 0

def format_size(size_bytes):
    """Formate la taille en format lisible."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def find_large_directories(root_path, max_results=20):
    """Trouve les dossiers les plus volumineux."""
    print(f"\n🔍 Analyse de: {root_path}")
    print("⏳ Cela peut prendre quelques instants...\n")
    
    dir_sizes = []
    
    try:
        for item in os.listdir(root_path):
            item_path = os.path.join(root_path, item)
            if os.path.isdir(item_path):
                size = get_size(item_path)
                if size > 0:
                    dir_sizes.append((item_path, size))
    except PermissionError:
        print(f"❌ Permission refusée pour: {root_path}")
        return []
    
    # Trier par taille décroissante
    dir_sizes.sort(key=lambda x: x[1], reverse=True)
    
    return dir_sizes[:max_results]

def find_large_files(root_path, max_results=20, min_size_mb=100):
    """Trouve les fichiers les plus volumineux."""
    print(f"\n🔍 Recherche de fichiers > {min_size_mb} MB dans: {root_path}")
    print("⏳ Cela peut prendre quelques instants...\n")
    
    large_files = []
    min_size_bytes = min_size_mb * 1024 * 1024
    
    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Ignorer certains dossiers
            dirnames[:] = [d for d in dirnames if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]
            
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(filepath)
                    if size >= min_size_bytes:
                        large_files.append((filepath, size))
                except (OSError, FileNotFoundError):
                    pass
    except PermissionError:
        print(f"❌ Permission refusée pour: {root_path}")
        return []
    
    # Trier par taille décroissante
    large_files.sort(key=lambda x: x[1], reverse=True)
    
    return large_files[:max_results]

def main():
    """Fonction principale."""
    print("=" * 70)
    print("🔍 RECHERCHE DE FICHIERS ET DOSSIERS VOLUMINEUX")
    print("=" * 70)
    
    # Analyser le répertoire home de l'utilisateur
    home_dir = os.path.expanduser("~")
    
    print(f"\n📁 Analyse du répertoire home: {home_dir}")
    
    # Trouver les gros dossiers
    print("\n" + "=" * 70)
    print("📂 TOP 20 DES DOSSIERS LES PLUS VOLUMINEUX")
    print("=" * 70)
    large_dirs = find_large_directories(home_dir, max_results=20)
    
    if large_dirs:
        total_size = 0
        for i, (dir_path, size) in enumerate(large_dirs, 1):
            total_size += size
            rel_path = os.path.relpath(dir_path, home_dir)
            print(f"{i:2d}. {format_size(size):>12s} - {rel_path}")
        
        print(f"\n   Total analysé: {format_size(total_size)}")
    else:
        print("   Aucun dossier volumineux trouvé")
    
    # Trouver les gros fichiers
    print("\n" + "=" * 70)
    print("📄 TOP 20 DES FICHIERS LES PLUS VOLUMINEUX (> 100 MB)")
    print("=" * 70)
    large_files = find_large_files(home_dir, max_results=20, min_size_mb=100)
    
    if large_files:
        total_size = 0
        for i, (file_path, size) in enumerate(large_files, 1):
            total_size += size
            rel_path = os.path.relpath(file_path, home_dir)
            print(f"{i:2d}. {format_size(size):>12s} - {rel_path}")
        
        print(f"\n   Total analysé: {format_size(total_size)}")
    else:
        print("   Aucun fichier volumineux trouvé")
    
    # Suggestions de nettoyage
    print("\n" + "=" * 70)
    print("💡 SUGGESTIONS DE NETTOYAGE")
    print("=" * 70)
    print("""
    Commandes utiles pour libérer de l'espace:
    
    1. Nettoyer les fichiers temporaires:
       rm -rf ~/Library/Caches/*
       rm -rf /tmp/*
    
    2. Nettoyer les logs système (macOS):
       sudo rm -rf /private/var/log/*
       sudo rm -rf ~/Library/Logs/*
    
    3. Nettoyer les téléchargements:
       ls -lh ~/Downloads | head -20
       # Supprimez manuellement les gros fichiers
    
    4. Nettoyer Docker (si installé):
       docker system prune -a --volumes
    
    5. Nettoyer les snapshots Time Machine (macOS):
       tmutil listlocalsnapshots /
       # Supprimez les anciens snapshots si nécessaire
    
    6. Vérifier l'espace utilisé par les applications:
       du -sh ~/Library/Application\ Support/* | sort -h | tail -20
    
    7. Nettoyer les fichiers .DS_Store:
       find ~ -name .DS_Store -delete
    
    ⚠️  ATTENTION: Vérifiez toujours avant de supprimer!
    """)
    
    print("=" * 70)

if __name__ == "__main__":
    main()
