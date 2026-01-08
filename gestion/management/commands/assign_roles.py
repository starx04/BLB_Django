from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Asignar roles por defecto a usuarios especiales (bibliotecario, bodeguero)'

    def handle(self, *args, **options):
        User = get_user_model()
        mapping = {
            'bibliotecario': 'Bibliotecario',
            'bodeguero': 'Bodeguero',
        }
        for username, group_name in mapping.items():
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Usuario '{username}' no existe. Omite."))
                continue
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
            # Remover el grupo 'Cliente' si existiera
            cliente_group, _ = Group.objects.get_or_create(name='Cliente')
            if user.groups.filter(name='Cliente').exists():
                user.groups.remove(cliente_group)
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Asignado grupo '{group_name}' a usuario '{username}'."))
        self.stdout.write(self.style.SUCCESS('Operación completada.'))