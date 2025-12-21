import requests

class OpenLibraryClient:
    """
    Cliente base para interactuar con la API de OpenLibrary.
    Provee métodos fundamentales para buscar libros e información de autores.
    """
    
    BASE_URL = "https://openlibrary.org"
    COVERS_URL = "https://covers.openlibrary.org/b/id"

    def __init__(self):
        # Usamos una sesión para optimizar conexiones si se hacen múltiples peticiones
        self.session = requests.Session()

    def get_book_by_isbn(self, isbn):
        """
        Obtiene los detalles de un libro dado su ISBN.
        
        Args:
            isbn (str): El ISBN del libro (10 o 13 dígitos).
            
        Returns:
            dict: Diccionario con los datos del libro o None si no se encuentra.
        """
        url = f"{self.BASE_URL}/api/books"
        params = {
            'bibkeys': f'ISBN:{isbn}',
            'format': 'json',
            'jscmd': 'data'  # 'data' nos da detalles como título, autor, portada
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status() # Lanza error si el status no es 200
            data = response.json()
            
            # La API retorna un dict con clave 'ISBN:xxxx', accedemos directo
            key = f"ISBN:{isbn}"
            return data.get(key)
            
        except requests.RequestException as e:
            print(f"Error de conexión con OpenLibrary API: {e}")
            return None

    def search_books(self, query, limit=5):
        """
        Busca libros por título o autor.
        
        Args:
            query (str): Término de búsqueda (ej. "Harry Potter").
            limit (int): Límite de resultados a retornar.
            
        Returns:
            list: Lista de documentos (libros) encontrados.
        """
        url = f"{self.BASE_URL}/search.json"
        params = {
            'q': query,
            'limit': limit
        }

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('docs', [])
        except requests.RequestException as e:
            print(f"Error buscando libros: {e}")
            return []

    def get_cover_url(self, cover_id, size='M'):
        """
        Construye la URL de la portada del libro.
        
        Args:
            cover_id (int): El ID de la portada (cover_i) retornado por la API.
            size (str): Tamaño de la imagen: 'S' (Small), 'M' (Medium), 'L' (Large).
            
        Returns:
            str: URL de la imagen.
        """
        if not cover_id:
            return None
        return f"{self.COVERS_URL}/{cover_id}-{size}.jpg"
