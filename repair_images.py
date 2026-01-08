import os
import django
import requests
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blb_django.settings')
django.setup()

from gestion.models import Libro

def fix_images():
    libros = Libro.objects.filter(imagen='')
    print(f"Encontrados {libros.count()} libros sin imagen.")
    headers = {'User-Agent': 'GestionBiblioteca/1.0 (contacto@biblioteca.local)'}
    
    for libro in libros:
        if libro.isbn:
            # Limpiar ISBN de guiones para la API
            isbn_clean = libro.isbn.replace('-', '').replace(' ', '')
            url = f"https://covers.openlibrary.org/b/isbn/{isbn_clean}-M.jpg"
            print(f"Intentando descargar para '{libro.titulo}' desde {url}...")
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                # OpenLibrary devuelve un 200 con un pixel de 1x1 si no encuentra la imagen.
                # Una imagen real suele tener mas de 1000 bytes.
                if resp.status_code == 200 and len(resp.content) > 1000:
                    file_name = f"libro_{libro.id}.jpg"
                    libro.imagen.save(file_name, ContentFile(resp.content), save=True)
                    print(f"  [OK] Imagen guardada para {libro.titulo}")
                else:
                    # Intentar con el ISBN original por si acaso
                    print(f"  [INFO] No se encontró imagen mayor a 1KB con ISBN limpio. Intentando con original: {libro.isbn}")
                    url_orig = f"https://covers.openlibrary.org/b/isbn/{libro.isbn}-M.jpg"
                    resp = requests.get(url_orig, headers=headers, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        file_name = f"libro_{libro.id}.jpg"
                        libro.imagen.save(file_name, ContentFile(resp.content), save=True)
                        print(f"  [OK] Imagen guardada para {libro.titulo} (ISBN original)")
                    else:
                        print(f"  [FAIL] No se encontró portada válida para {libro.titulo}")
            except Exception as e:
                print(f"  [ERROR] Error con {libro.titulo}: {e}")

if __name__ == "__main__":
    fix_images()
