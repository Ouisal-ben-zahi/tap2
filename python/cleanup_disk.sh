#!/bin/bash
# Script de nettoyage rapide pour libérer de l'espace disque sur macOS

echo "============================================================"
echo "🧹 NETTOYAGE RAPIDE DU DISQUE"
echo "============================================================"
echo ""
echo "⚠️  Ce script va nettoyer plusieurs types de fichiers."
echo "⚠️  Vérifiez l'espace libéré après chaque étape."
echo ""

# Fonction pour afficher l'espace disque
show_disk_space() {
    echo "📊 Espace disque actuel:"
    df -h / | tail -1 | awk '{print "   Utilisé: " $3 " / " $2 " (" $5 ")"}'
    echo ""
}

show_disk_space

# 1. Nettoyer les caches utilisateur
echo "1️⃣  Nettoyage des caches utilisateur..."
CACHE_SIZE=$(du -sh ~/Library/Caches 2>/dev/null | cut -f1)
echo "   Taille actuelle: $CACHE_SIZE"
read -p "   Supprimer les caches? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ~/Library/Caches/*
    echo "   ✅ Caches supprimés"
    show_disk_space
fi

# 2. Nettoyer les logs utilisateur
echo ""
echo "2️⃣  Nettoyage des logs utilisateur..."
LOG_SIZE=$(du -sh ~/Library/Logs 2>/dev/null | cut -f1)
echo "   Taille actuelle: $LOG_SIZE"
read -p "   Supprimer les logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ~/Library/Logs/*
    echo "   ✅ Logs supprimés"
    show_disk_space
fi

# 3. Nettoyer les fichiers temporaires
echo ""
echo "3️⃣  Nettoyage des fichiers temporaires..."
TMP_SIZE=$(du -sh /tmp 2>/dev/null | cut -f1)
echo "   Taille actuelle: $TMP_SIZE"
read -p "   Supprimer les fichiers temporaires? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo rm -rf /tmp/*
    echo "   ✅ Fichiers temporaires supprimés"
    show_disk_space
fi

# 4. Nettoyer les fichiers .DS_Store
echo ""
echo "4️⃣  Nettoyage des fichiers .DS_Store..."
read -p "   Supprimer les fichiers .DS_Store? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    find ~ -name .DS_Store -delete 2>/dev/null
    echo "   ✅ Fichiers .DS_Store supprimés"
    show_disk_space
fi

# 5. Nettoyer Docker (si installé)
if command -v docker &> /dev/null; then
    echo ""
    echo "5️⃣  Nettoyage Docker..."
    DOCKER_SIZE=$(docker system df 2>/dev/null | tail -1 | awk '{print $3}')
    echo "   Espace Docker utilisé: $DOCKER_SIZE"
    read -p "   Nettoyer Docker (images, conteneurs, volumes)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -a --volumes -f
        echo "   ✅ Docker nettoyé"
        show_disk_space
    fi
fi

# 6. Nettoyer les snapshots Time Machine locaux
echo ""
echo "6️⃣  Snapshots Time Machine locaux..."
SNAPSHOTS=$(tmutil listlocalsnapshots / 2>/dev/null | wc -l | tr -d ' ')
if [ "$SNAPSHOTS" -gt 0 ]; then
    echo "   Nombre de snapshots: $SNAPSHOTS"
    read -p "   Supprimer les snapshots locaux? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for snapshot in $(tmutil listlocalsnapshots / | cut -d' ' -f4); do
            sudo tmutil deletelocalsnapshots "$snapshot"
        done
        echo "   ✅ Snapshots supprimés"
        show_disk_space
    fi
else
    echo "   Aucun snapshot local trouvé"
fi

echo ""
echo "============================================================"
echo "✅ NETTOYAGE TERMINÉ"
echo "============================================================"
show_disk_space

echo ""
echo "💡 Pour trouver les fichiers les plus volumineux:"
echo "   python find_large_files.py"
echo ""
