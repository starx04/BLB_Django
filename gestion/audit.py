from django.db import models
from django.conf import settings
from django.utils import timezone

class RegistroAuditoria(models.Model):
    """
    Modelo para registrar todas las acciones importantes del sistema.
    Permite generar reportes de actividad y trazabilidad.
    """
    ACCIONES = (
        ('crear_prestamo', 'Crear Préstamo'),
        ('finalizar_prestamo', 'Finalizar Préstamo'),
        ('renovar_prestamo', 'Renovar Préstamo'),
        ('pagar_multa', 'Pagar Multa'),
        ('crear_libro', 'Crear Libro'),
        ('crear_autor', 'Crear Autor'),
        ('crear_usuario', 'Crear Usuario'),
    )
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='acciones_realizadas')
    accion = models.CharField(max_length=50, choices=ACCIONES)
    descripcion = models.TextField()
    fecha_hora = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Campos opcionales para referencias
    prestamo_id = models.IntegerField(null=True, blank=True)
    multa_id = models.IntegerField(null=True, blank=True)
    libro_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'
    
    def __str__(self):
        return f"{self.get_accion_display()} por {self.usuario} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"
