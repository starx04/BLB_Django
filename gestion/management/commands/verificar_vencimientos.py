from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from gestion.models import Prestamos

class Command(BaseCommand):
    help = 'Verifica prestamos vencidos, aplica multas y notifica usuarios.'

    def handle(self, *args, **kwargs):
        hoy = timezone.now().date()
        # 1. Buscar prestamos que aun figuran como 'prestado' pero ya vencieron
        prestamos_vencidos = Prestamos.objects.filter(estado='prestado', fecha_max__lt=hoy)
        
        count = 0
        for prestamo in prestamos_vencidos:
            # Cambiar estado a multado
            prestamo.estado = 'multado'
            prestamo.save()
            
            # Calcular multa preliminar
            dias_retraso = (hoy - prestamo.fecha_max).days
            monto_multa = dias_retraso * 0.50 # Tarifa hardcodeada en modelo es 0.50
            
            # Enviar correo
            try:
                usuario = prestamo.usuario
                if usuario.email:
                    asunto = f"AVISO DE MULTA: Préstamo Vencido - {prestamo.codigo}"
                    mensaje = f"""
Hola {usuario.username},

Te informamos que el préstamo del libro "{prestamo.libro.titulo}" ha vencido.

Detalles:
- Código Préstamo: {prestamo.codigo}
- Fecha Préstamo: {prestamo.fecha}
- Fecha Límite: {prestamo.fecha_max}
- Días de retraso: {dias_retraso}
- Multa acumulada hasta hoy: ${monto_multa:.2f}

El estado de tu préstamo ha pasado a 'MULTADO'. Por favor acércate a la biblioteca para regularizar tu situación.

Atentamente,
Biblioteca Local
"""
                    send_mail(
                        asunto,
                        mensaje,
                        settings.DEFAULT_FROM_EMAIL or 'noreply@biblioteca.local',
                        [usuario.email],
                        fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f'Correo enviado a {usuario.email}'))
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error enviando correo a {usuario.username}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'Proceso completado. {count} préstamos actualizados a multado.'))
