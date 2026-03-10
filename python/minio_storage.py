"""
Module pour gérer le stockage des fichiers dans MinIO
"""

import os
from io import BytesIO
from typing import Optional, Tuple
from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

load_dotenv()

# Configuration MinIO depuis les variables d'environnement
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'False').lower() == 'true'
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'tap-files')


class MinIOStorage:
    """Classe pour gérer les opérations MinIO."""
    
    def __init__(self):
        """Initialise le client MinIO."""
        try:
            self.client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            self.bucket_name = MINIO_BUCKET
            self._ensure_bucket_exists()
            print(f"✅ MinIO client initialisé: {MINIO_ENDPOINT}/{self.bucket_name}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Erreur d'initialisation MinIO:")
            print(f"   Endpoint: {MINIO_ENDPOINT}")
            print(f"   Bucket: {MINIO_BUCKET}")
            print(f"   Secure: {MINIO_SECURE}")
            print(f"   Erreur: {e}")
            print(f"   Détails:\n{error_details}")
            self.client = None
    
    def _ensure_bucket_exists(self):
        """Crée le bucket s'il n'existe pas."""
        if not self.client:
            return
        
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"✅ Bucket '{self.bucket_name}' créé")
        except S3Error as e:
            print(f"⚠️  Erreur lors de la création du bucket: {e}")
    
    def upload_file(
        self, 
        file_bytes: bytes, 
        object_name: str, 
        content_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload un fichier vers MinIO.
        
        Args:
            file_bytes: Contenu binaire du fichier
            object_name: Nom de l'objet dans MinIO (chemin)
            content_type: Type MIME du fichier (optionnel)
            
        Returns:
            Tuple (success, url, error_message)
        """
        if not self.client:
            return False, None, "Client MinIO non initialisé"
        
        try:
            # Déterminer le content_type si non fourni
            if not content_type:
                content_type = self._guess_content_type(object_name)
            
            # Upload du fichier
            self.client.put_object(
                self.bucket_name,
                object_name,
                BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type
            )
            
            # Générer l'URL
            url = self._get_file_url(object_name)
            
            print(f"✅ Fichier uploadé vers MinIO: {object_name}")
            return True, url, None
            
        except S3Error as e:
            error_msg = f"Erreur MinIO: {e}"
            print(f"❌ {error_msg}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Erreur inattendue: {e}"
            print(f"❌ {error_msg}")
            return False, None, error_msg
    
    def upload_file_from_path(
        self, 
        file_path: str, 
        object_name: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload un fichier depuis le système de fichiers local.
        
        Args:
            file_path: Chemin vers le fichier local
            object_name: Nom de l'objet dans MinIO (si None, utilise le nom du fichier)
            content_type: Type MIME du fichier (optionnel)
            
        Returns:
            Tuple (success, url, error_message)
        """
        if not os.path.exists(file_path):
            return False, None, f"Fichier introuvable: {file_path}"
        
        if not object_name:
            object_name = os.path.basename(file_path)
        
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        return self.upload_file(file_bytes, object_name, content_type)
    
    def get_file_url(self, object_name: str) -> Optional[str]:
        """
        Génère l'URL d'accès à un fichier.
        
        Args:
            object_name: Nom de l'objet dans MinIO
            
        Returns:
            URL du fichier ou None
        """
        if not self.client:
            return None
        
        return self._get_file_url(object_name)
    
    def _get_file_url(self, object_name: str) -> str:
        """Génère l'URL complète du fichier."""
        protocol = "https" if MINIO_SECURE else "http"
        return f"{protocol}://{MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"
    
    def _guess_content_type(self, filename: str) -> str:
        """Devine le type MIME à partir de l'extension du fichier."""
        extension = os.path.splitext(filename)[1].lower()
        
        content_types = {
            '.pdf': 'application/pdf',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
        }
        
        return content_types.get(extension, 'application/octet-stream')
    
    def object_exists(self, object_name: str) -> bool:
        """
        Vérifie si un objet existe dans MinIO (sans le télécharger).
        Ne log pas d'erreur si l'objet n'existe pas (cas normal).
        """
        if not self.client:
            return False
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                return False
            print(f"❌ Erreur MinIO stat_object: {e}")
            return False
        except Exception:
            return False

    def download_file(self, object_name: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
        """
        Télécharge un fichier depuis MinIO.
        
        Args:
            object_name: Nom de l'objet dans MinIO
            
        Returns:
            Tuple (success, file_bytes, error_message)
        """
        if not self.client:
            return False, None, "Client MinIO non initialisé"
        
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            file_bytes = response.read()
            response.close()
            response.release_conn()
            print(f"✅ Fichier téléchargé depuis MinIO: {object_name}")
            return True, file_bytes, None
        except S3Error as e:
            error_msg = f"Erreur MinIO lors du téléchargement: {e}"
            print(f"❌ {error_msg}")
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Erreur inattendue lors du téléchargement: {e}"
            print(f"❌ {error_msg}")
            return False, None, error_msg
    
    def delete_file(self, object_name: str) -> Tuple[bool, Optional[str]]:
        """
        Supprime un fichier de MinIO.
        
        Args:
            object_name: Nom de l'objet à supprimer
            
        Returns:
            Tuple (success, error_message)
        """
        if not self.client:
            return False, "Client MinIO non initialisé"
        
        try:
            self.client.remove_object(self.bucket_name, object_name)
            print(f"✅ Fichier supprimé de MinIO: {object_name}")
            return True, None
        except S3Error as e:
            error_msg = f"Erreur lors de la suppression: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def get_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """
        Génère une URL signée pour accéder au fichier sans credentials.
        L'URL est valide pour une durée limitée.
        
        Args:
            object_name: Nom de l'objet dans MinIO
            expires: Durée de validité en secondes (défaut: 1 heure)
            
        Returns:
            URL signée ou None
        """
        if not self.client:
            return None
        
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                self.bucket_name,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except Exception as e:
            print(f"❌ Erreur génération URL signée: {e}")
            return None


# Instance globale
_minio_storage = None

def get_minio_storage() -> MinIOStorage:
    """
    Retourne l'instance globale de MinIOStorage.
    Réessaie l'initialisation si le client n'est pas initialisé.
    """
    global _minio_storage
    if _minio_storage is None or _minio_storage.client is None:
        # Créer ou recréer l'instance si elle n'existe pas ou si le client n'est pas initialisé
        print(f"🔄 Tentative d'initialisation MinIO...")
        _minio_storage = MinIOStorage()
        if _minio_storage.client is None:
            print(f"⚠️  MinIO n'est toujours pas accessible. Vérifiez que le serveur MinIO est lancé et accessible à {MINIO_ENDPOINT}")
    return _minio_storage

