import requests

class ClienteOpenLibrary:
    """
    Cliente para interactuar con la API de OpenLibrary.
    Permite buscar libros e información de autores.
    """
    
    URL_BASE = "https://openlibrary.org"
    URL_PORTADAS = "https://covers.openlibrary.org/b/id"
    URL_PORTADAS_ISBN = "https://covers.openlibrary.org/b/isbn"

    def __init__(self):
        self.sesion = requests.Session()
        # Header recomendado por OpenLibrary para buenas prácticas
        self.sesion.headers.update({
            'User-Agent': 'GestionBiblioteca/1.0 (contacto@biblioteca.local)'
        })

    def obtener_libro_por_isbn(self, isbn):
        """
        Obtiene los metadatos de un libro dado su ISBN.
        Retorna: Diccionario con datos o None si falla.
        """
        # [CRÍTICO] Endpoint oficial de OpenLibrary para datos estructurados
        url = f"{self.URL_BASE}/api/books"
        params = {
            'bibkeys': f'ISBN:{isbn}',
            'format': 'json',
            'jscmd': 'data' # 'data' es crucial para obtener autores y portadas en un solo request
        }

        try:
            respuesta = self.sesion.get(url, params=params)
            respuesta.raise_for_status()
            datos = respuesta.json()
            return datos.get(f"ISBN:{isbn}")
            
        except requests.RequestException:
            return None

    def buscar_libros(self, consulta, limite=5):
        """
        Realiza una búsqueda de texto completo (título, autor) en la biblioteca.
        """
        url = f"{self.URL_BASE}/search.json"
        params = {'q': consulta, 'limit': limite}

        try:
            respuesta = self.sesion.get(url, params=params)
            respuesta.raise_for_status() # [IMPORTANTE] Lanza error si el status HTTP no es 200 OK
            datos = respuesta.json()
            return datos.get('docs', [])
        except requests.RequestException:
            return []

    def obtener_url_portada(self, id_portada, tamano='M'):
        """Genera la URL de la portada usando el ID."""
        if not id_portada:
            return None
        return f"{self.URL_PORTADAS}/{id_portada}-{tamano}.jpg"

    def obtener_url_portada_isbn(self, isbn, tamano='M'):
        """Genera la URL de la portada usando el ISBN."""
        if not isbn:
            return None
        return f"{self.URL_PORTADAS_ISBN}/{isbn}-{tamano}.jpg"
