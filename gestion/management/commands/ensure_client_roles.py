from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = "Asignar el grupo 'Cliente' a usuarios regulares que no tienen un rol asignado"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Mostrar qué se cambiaría sin guardar')

    def handle(self, *args, **options):
        User = get_user_model()
        cliente_group, _ = Group.objects.get_or_create(name='Cliente')
        personal_roles = ['Bibliotecario', 'Bodeguero', 'Administrador']

        users = User.objects.filter(is_superuser=False, is_staff=False)
        candidates = []
        for u in users:
            # Si ya tiene grupo Cliente, saltar
            if u.groups.filter(name='Cliente').exists():
                continue
            # Si tiene algún rol de personal, saltar
            if u.groups.filter(name__in=personal_roles).exists():
                continue
            # Usuario candidato para ser Cliente
            candidates.append(u)

        if not candidates:
            self.stdout.write(self.style.SUCCESS('No se encontraron usuarios para convertir a Cliente.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.NOTICE('Dry run — usuarios que se asignarían al grupo Cliente:'))
            for u in candidates:
                self.stdout.write(f" - {u.username} (id={u.id})")
            self.stdout.write(self.style.NOTICE(f'Total: {len(candidates)}'))
            return

        count = 0
        for u in candidates:
            u.groups.add(cliente_group)
            u.save()
            count += 1
            self.stdout.write(self.style.SUCCESS(f"Asignado grupo 'Cliente' a usuario '{u.username}' (id={u.id})"))

        self.stdout.write(self.style.SUCCESS(f'Total asignados: {count}'))