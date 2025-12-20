from django.urls import reverse
from django.test import TestCase
from gestion.models import Autor, Libro, Prestamos
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class LibroModelTest(TestCase):
    @classmethod
    def setUpTestData(self):
        autor = Autor.objects.create(nombre="Issac", apellido="Asimov", bibliografia="Cualquier dato")
        Libro.objects.create(titulo="Fundacion", autor=autor, disponible=True)
    
    def test_str_devuelve_titulo(self):
        libro = Libro.objects.get(titulo="Fundacion")
        self.assertEqual(str(libro), "Fundacion")
class PrestamoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuario = User.objects.create_user(username="Ax", password="Ax23@fer")
        # Need to create Autor first
        autor = Autor.objects.create(nombre="Isaac", apellido="Asimov")
        libro = Libro.objects.create(titulo="I Robot", autor=autor, disponible=True)
        cls.prestamo = Prestamos.objects.create(
            libro=libro,
            usuario=usuario,
            fecha=timezone.now(),
            fecha_max=timezone.now() + timedelta(days=30)
            )        
    def test_libro_disponible(self):
        # By default model creation does not change availablity (logic is in view)
        self.prestamo.refresh_from_db()
        self.assertTrue(self.prestamo.libro.disponible)
        # Retraso checks
        self.assertEqual(self.prestamo.dias_retraso, 0)
 

class PrestamoUsuarioViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username="Ax", password="Ax23@fer") 
        cls.user2 = User.objects.create_user(username="Bx", password="Ax23@fer")

    def test_redirige_no_login(self):
        resp = self.client.get(reverse('crear_autor'))
        self.assertEqual(resp.status_code, 302)
        # Redirect URL will depend on settings.LOGIN_URL which is 'login'
        # The next param is urlencoded, but assertRedirects handles checking nicely usually
        self.assertRedirects(resp, '/login/?next=/autores/nuevo')

    def test_carga_login(self):
        resp = self.client.login(username="Ax", password="Ax23@fer")
        self.assertTrue(resp)
        resp1 = self.client.get(reverse('crear_autor'))
        self.assertEqual(resp1.status_code, 200)
        self.assertTemplateUsed(resp1, 'crear_autor.html')
