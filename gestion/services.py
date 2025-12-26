import requests

class ClienteOpenLibrary:
    """
    Cliente para interactuar con la API de OpenLibrary.
    Permite buscar libros e información de autores.
    """
    
    URL_BASE = "https://openlibrary.org"
    URL_PORTADAS = "https://covers.openlibrary.org/b/id"

    def __init__(self):
        self.sesion = requests.Session()

    def obtener_libro_por_isbn(self, isbn):
        """Obtiene detalles de un libro por su ISBN."""
        url = f"{self.URL_BASE}/api/books"
        params = {
            'bibkeys': f'ISBN:{isbn}',
            'format': 'json',
            'jscmd': 'data'
        }

        try:
            respuesta = self.sesion.get(url, params=params)
            respuesta.raise_for_status()
            datos = respuesta.json()
            return datos.get(f"ISBN:{isbn}")
            
        except requests.RequestException:
            return None

    def buscar_libros(self, consulta, limite=5):
        """Busca libros por título o autor."""
        url = f"{self.URL_BASE}/search.json"
        params = {'q': consulta, 'limit': limite}

        try:
            respuesta = self.sesion.get(url, params=params)
            respuesta.raise_for_status()
            datos = respuesta.json()
            return datos.get('docs', [])
        except requests.RequestException:
            return []

    def obtener_url_portada(self, id_portada, tamano='M'):
        """Genera la URL de la portada."""
        if not id_portada:
            return None
        return f"{self.URL_PORTADAS}/{id_portada}-{tamano}.jpg"
