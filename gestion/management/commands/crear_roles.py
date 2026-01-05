from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from gestion.models import Libro, Prestamos, Multa, PerfilUsuario

class Command(BaseCommand):
    help = 'Crea los grupos de usuarios y asigna permisos segun roles'

    def handle(self, *args, **kwargs):
        # Limpiar grupos existentes
        Group.objects.all().delete()
        
        # ===== GRUPO: CLIENTE =====
        grupo_cliente, _ = Group.objects.get_or_create(name='Cliente')
        permisos_cliente = [
            # Ver sus propios prestamos y multas
            Permission.objects.get(codename='view_prestamos', content_type__app_label='gestion'),
            Permission.objects.get(codename='view_multa', content_type__app_label='gestion'),
            # Ver libros disponibles
            Permission.objects.get(codename='view_libro', content_type__app_label='gestion'),
        ]
        grupo_cliente.permissions.set(permisos_cliente)
        self.stdout.write(self.style.SUCCESS('[OK] Grupo CLIENTE creado'))

        # ===== GRUPO: BIBLIOTECARIO =====
        grupo_bibliotecario, _ = Group.objects.get_or_create(name='Bibliotecario')
        permisos_bibliotecario = [
            # Gestion completa de prestamos
            Permission.objects.get(codename='add_prestamos', content_type__app_label='gestion'),
            Permission.objects.get(codename='change_prestamos', content_type__app_label='gestion'),
            Permission.objects.get(codename='delete_prestamos', content_type__app_label='gestion'),
            Permission.objects.get(codename='view_prestamos', content_type__app_label='gestion'),
            # Ver y gestionar multas
            Permission.objects.get(codename='view_multa', content_type__app_label='gestion'),
            Permission.objects.get(codename='change_multa', content_type__app_label='gestion'),
            # Ver libros y usuarios
            Permission.objects.get(codename='view_libro', content_type__app_label='gestion'),
            Permission.objects.get(codename='view_user', content_type__app_label='auth'),
        ]
        grupo_bibliotecario.permissions.set(permisos_bibliotecario)
        self.stdout.write(self.style.SUCCESS('[OK] Grupo BIBLIOTECARIO creado'))

        # ===== GRUPO: BODEGUERO =====
        grupo_bodeguero, _ = Group.objects.get_or_create(name='Bodeguero')
        permisos_bodeguero = [
            # Gestion completa de libros
            Permission.objects.get(codename='add_libro', content_type__app_label='gestion'),
            Permission.objects.get(codename='change_libro', content_type__app_label='gestion'),
            Permission.objects.get(codename='delete_libro', content_type__app_label='gestion'),
            Permission.objects.get(codename='view_libro', content_type__app_label='gestion'),
            # Gestion de autores
            Permission.objects.get(codename='add_autor', content_type__app_label='gestion'),
            Permission.objects.get(codename='change_autor', content_type__app_label='gestion'),
            Permission.objects.get(codename='delete_autor', content_type__app_label='gestion'),
            Permission.objects.get(codename='view_autor', content_type__app_label='gestion'),
        ]
        grupo_bodeguero.permissions.set(permisos_bodeguero)
        self.stdout.write(self.style.SUCCESS('[OK] Grupo BODEGUERO creado'))

        # ===== CREAR USUARIOS DE PRUEBA =====
        
        # 1. ADMINISTRADOR (Superusuario Principal)
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@biblioteca.local',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema'
            )
            self.stdout.write(self.style.SUCCESS('[OK] Usuario ADMIN creado (Superusuario)'))

        # 1.1 SUPERUSUARIO DEL SISTEMA (Adicional solicitado)
        if not User.objects.filter(username='superadmin').exists():
            super_user = User.objects.create_superuser(
                username='superadmin',
                email='superadmin@biblioteca.local',
                password='super123',
                first_name='Super',
                last_name='Admin'
            )
            self.stdout.write(self.style.SUCCESS('[OK] Usuario SUPERADMIN creado (Superusuario del Sistema)'))

        # 2. BIBLIOTECARIO
        if not User.objects.filter(username='bibliotecario').exists():
            biblio = User.objects.create_user(
                username='bibliotecario',
                email='bibliotecario@biblioteca.local',
                password='biblio123',
                first_name='Juan',
                last_name='Perez'
            )
            biblio.groups.add(grupo_bibliotecario)
            self.stdout.write(self.style.SUCCESS('[OK] Usuario BIBLIOTECARIO creado'))

        # 3. BODEGUERO
        if not User.objects.filter(username='bodeguero').exists():
            bodeg = User.objects.create_user(
                username='bodeguero',
                email='bodeguero@biblioteca.local',
                password='bodega123',
                first_name='Carlos',
                last_name='Ramirez'
            )
            bodeg.groups.add(grupo_bodeguero)
            self.stdout.write(self.style.SUCCESS('[OK] Usuario BODEGUERO creado'))

        # 4. CLIENTE
        if not User.objects.filter(username='cliente').exists():
            cliente = User.objects.create_user(
                username='cliente',
                email='cliente@ejemplo.com',
                password='cliente123',
                first_name='Maria',
                last_name='Gonzalez'
            )
            cliente.groups.add(grupo_cliente)
            # Asignar DNI al perfil
            cliente.perfil.dni = '12345678'
            cliente.perfil.save()
            self.stdout.write(self.style.SUCCESS('[OK] Usuario CLIENTE creado'))

        self.stdout.write(self.style.SUCCESS('\n=== RESUMEN DE USUARIOS Y ROLES ==='))
        self.stdout.write('1. ADMIN (Superusuario) -> admin / admin123')
        self.stdout.write('2. SUPERADMIN (Superusuario Sistema) -> superadmin / super123')
        self.stdout.write('3. BIBLIOTECARIO (Prestamos) -> bibliotecario / biblio123')
        self.stdout.write('4. BODEGUERO (Libros) -> bodeguero / bodega123')
        self.stdout.write('5. CLIENTE (Usuario final) -> cliente / cliente123')
