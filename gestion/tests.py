from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal
from gestion.models import Autor, Libro, Prestamos, Multa, PerfilUsuario

class TestModelosBiblioteca(TestCase):

    def setUp(self):
        """Configuración inicial para todas las pruebas."""
        # 1. Crear usuarios y perfiles
        self.usuario = User.objects.create_user(username='lector1', password='password123')
        # El perfil se crea automáticamente por signal, lo recuperamos
        self.perfil = self.usuario.perfil
        
        # 2. Crear datos base (Autor, Libro)
        self.autor = Autor.objects.create(nombre="Gabriel", apellido="Garcia Marquez")
        self.libro = Libro.objects.create(
            titulo="Cien Años de Soledad",
            autor=self.autor,
            stock=5,
            isbn="1234567890123"
        )

    # --- TESTS DE PERFIL USUARIO ---
    def test_perfil_creacion_automatica(self):
        """Verifica que al crear un User se crea su PerfilUsuario y genera codigo socio."""
        self.assertIsNotNone(self.perfil)
        self.assertTrue(self.perfil.codigo_socio.startswith("SOC-"))
    
    # --- TESTS DE LIBRO ---
    def test_libro_disponibilidad(self):
        """Verifica el cálculo de stock disponible."""
        # Stock inicial es 5
        self.assertEqual(self.libro.disponibles, 5)
        self.assertTrue(self.libro.esta_disponible)
        
        # Simulamos 5 prestamos activos (sin devolver)
        for _ in range(5):
            u = User.objects.create_user(username=f'u{_}', password='p')
            Prestamos.objects.create(libro=self.libro, usuario=u, fecha=timezone.now(), fecha_max=timezone.now())
        
        # Ahora debería ser 0
        self.assertEqual(self.libro.disponibles, 0)
        self.assertFalse(self.libro.esta_disponible)

    # --- TESTS DE PRESTAMOS ---
    def test_prestamo_ciclo_vida_normal(self):
        """Prueba flujo normal: Crear -> Confirmar -> Devolver (A tiempo)."""
        prestamo = Prestamos.objects.create(libro=self.libro, usuario=self.usuario)
        
        # 1. Estado inicial Borrador
        self.assertEqual(prestamo.estado, 'borrador')
        
        # 2. Confirmar (Pasa a Prestado y genera fecha max)
        prestamo.confirmar()
        self.assertEqual(prestamo.estado, 'prestado')
        self.assertIsNotNone(prestamo.fecha_max)
        # Verifica que fecha max es 7 dias despues (margen de error pequeño por segundos)
        dias_diferencia = (prestamo.fecha_max - prestamo.fecha).days
        self.assertEqual(dias_diferencia, 7)
        
        # 3. Finalizar (Devolución a tiempo)
        prestamo.finalizar()
        self.assertEqual(prestamo.estado, 'devuelto')
        self.assertEqual(prestamo.Multa.count(), 0) # No debe haber multas

    def test_prestamo_vencido_genera_multa(self):
        """Prueba que finalizar un préstamo tarde genera multa automática."""
        # Creamos prestamo QUE VENCIÓ AYER
        ayer = timezone.now().date() - timezone.timedelta(days=1)
        hace_una_semana = timezone.now().date() - timezone.timedelta(days=8)
        
        prestamo = Prestamos.objects.create(
            libro=self.libro, 
            usuario=self.usuario,
            estado='prestado',
            fecha=hace_una_semana,
            fecha_max=ayer # Vencía ayer
        )
        
        # Verificamos que detecta retraso
        self.assertEqual(prestamo.dias_retraso, 1)
        
        # Finalizamos hoy
        prestamo.finalizar()
        
        # Debe haberse creado 1 multa de tipo retraso
        self.assertEqual(prestamo.Multa.count(), 1)
        multa = prestamo.Multa.first()
        self.assertEqual(multa.tipo, 'r')
        self.assertEqual(multa.monto, Decimal('0.50')) # 1 dia * 0.50

    def test_prestamo_perdida_excluyente(self):
        """Prueba que reportar Pérdida NO genera multa extra por retraso."""
        # Prestamo MUY vencido (10 dias)
        fecha_vencida = timezone.now().date() - timezone.timedelta(days=10)
        
        prestamo = Prestamos.objects.create(
            libro=self.libro, 
            usuario=self.usuario, 
            estado='prestado',
            fecha_max=fecha_vencida
        )
        
        # Finalizamos reportando PERDIDA por valor de 50.00
        prestamo.finalizar(tipo_multa='p', monto_multa=50.00)
        
        # Solo debe existir la multa de perdida
        self.assertEqual(prestamo.Multa.count(), 1)
        multa = prestamo.Multa.first()
        self.assertEqual(multa.tipo, 'p')
        self.assertEqual(multa.monto, Decimal('50.00'))
        
    def test_prestamo_dano_acumulativo(self):
        """Prueba que reportar Daño SI acumula con multa por retraso."""
        # Prestamo vencido 2 dias ($1.00 de retraso)
        fecha_vencida = timezone.now().date() - timezone.timedelta(days=2)
        
        prestamo = Prestamos.objects.create(
            libro=self.libro, 
            usuario=self.usuario, 
            estado='prestado',
            fecha_max=fecha_vencida
        )
        
        # Finalizamos reportando DAÑO por 20.00
        prestamo.finalizar(tipo_multa='d', monto_multa=20.00)
        
        # Deben existir 2 multas (Daño + Retraso)
        self.assertEqual(prestamo.Multa.count(), 2)
        
        tipos = [m.tipo for m in prestamo.Multa.all()]
        montos = sorted([m.monto for m in prestamo.Multa.all()])
        
        self.assertIn('d', tipos)
        self.assertIn('r', tipos)
        self.assertEqual(montos, [Decimal('1.00'), Decimal('20.00')]) # 1.00 retraso, 20.00 daño

    # --- TESTS DE MULTA ---
    def test_multa_generacion_codigo(self):
        """Verifica que las multas generan su código único al guardarse."""
        prestamo = Prestamos.objects.create(libro=self.libro, usuario=self.usuario)
        multa = Multa.objects.create(prestamo=prestamo, tipo='d', monto=10)
        
        self.assertIsNotNone(multa.codigo)
        self.assertTrue(multa.codigo.startswith("MULT-"))
