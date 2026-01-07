from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import RegistroAuditoria

@receiver(user_logged_in)
def registrar_inicio_sesion(sender, request, user, **kwargs):
    RegistroAuditoria.objects.create(
        usuario=user,
        accion='inicio_sesion',
        descripcion=f"El usuario {user.username} ha iniciado sesión.",
        ip_address=request.META.get('REMOTE_ADDR')
    )

@receiver(user_logged_out)
def registrar_cierre_sesion(sender, request, user, **kwargs):
    if user:
        RegistroAuditoria.objects.create(
            usuario=user,
            accion='cierre_sesion',
            descripcion=f"El usuario {user.username} ha cerrado sesión.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
