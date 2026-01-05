from django.shortcuts import render, redirect, get_object_or_404
import requests
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponseForbidden
from django.core.files.base import ContentFile
from django.contrib.auth import login
from django.db.models import Sum

from .models import Libro, Prestamos, Multa, Autor, RegistroAuditoria

# --- DECORADORES DE ROLES ---
def es_admin(user):
    return user.is_superuser

def es_bibliotecario(user):
    return user.groups.filter(name='Bibliotecario').exists() or user.is_superuser

def es_bodeguero(user):
    return user.groups.filter(name='Bodeguero').exists() or user.is_superuser

def es_cliente(user):
    return user.groups.filter(name='Cliente').exists()

# --- VISTAS PÚBLICAS ---

def index(request):
    """Vista pública del Dashboard - No requiere login."""
    title = settings.TITLE
    total_libros = Libro.objects.count()
    prestamos_activos = Prestamos.objects.filter(estado='prestado').count()
    multas_pendientes = Multa.objects.filter(pagada=False).aggregate(total=Sum('monto'))['total'] or 0
    usuarios_registrados = User.objects.count()
    libros_recientes = Libro.objects.order_by('-id')[:5]

    context = {
        'titulo': title,
        'total_libros': total_libros,
        'prestamos_activos': prestamos_activos,
        'multas_pendientes': multas_pendientes,
        'usuarios_registrados': usuarios_registrados,
        'libros_recientes': libros_recientes
    }
    return render(request, 'home.html', context)

def lista_libros(request):
    """Vista pública de catálogo de libros."""
    libros = Libro.objects.all()
    return render(request, 'libros.html', {'libros': libros})

def lista_autores(request):
    """Vista pública de autores."""
    autores = Autor.objects.all()
    return render(request, 'autores.html', {'autores': autores})

# --- SECCION LIBROS (PERSONAL) ---

@user_passes_test(es_bodeguero)
@login_required
def crear_libros(request):
    from .models import Categoria
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        nombre_autor_texto = request.POST.get('autor_texto')
        isbn = request.POST.get('isbn')
        stock = request.POST.get('stock', 1)
        
        nombre = nombre_autor_texto.strip()
        partes = nombre.split(' ')
        nombre_nuevo = " ".join(partes[:-1]) if len(partes) > 1 else nombre
        apellido_nuevo = partes[-1] if len(partes) > 1 else ""
        
        autor_final, _ = Autor.objects.get_or_create(
            nombre__iexact=nombre_nuevo, 
            apellido__iexact=apellido_nuevo, 
            defaults={'nombre': nombre_nuevo, 'apellido': apellido_nuevo}
        )
        
        nuevo_libro = Libro.objects.create(titulo=titulo, autor=autor_final, stock=int(stock), isbn=isbn)
        
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_libro',
            descripcion=f"Bodeguero creó libro: {titulo}",
            libro_id=nuevo_libro.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return redirect('lista_libros')
    return render(request, 'crear_libros.html', {'autores': autores, 'categorias': categorias})

@user_passes_test(es_bodeguero)
@login_required
def crear_autor(request, id=None):
    autor = get_object_or_404(Autor, id=id) if id else None
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        if autor:
            autor.nombre, autor.apellido = nombre, apellido
            autor.save()
        else:
            Autor.objects.create(nombre=nombre, apellido=apellido)
        return redirect('lista_autores')
    return render(request, 'crear_autor.html', {'autor': autor, 'mode': 'Editar' if id else 'Nuevo'})

# --- SECCION PRESTAMOS ---

@login_required
def lista_prestamos(request):
    """
    CLIENTE: Ve solo sus préstamos.
    PERSONAL: Ve todos.
    """
    if es_bibliotecario(request.user):
        prestamos = Prestamos.objects.all().order_by('-fecha')
    else:
        prestamos = Prestamos.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'prestamos.html', {'prestamos': prestamos})

@login_required
def crear_prestamo(request):
    """
    CLIENTE: Crea una solicitud.
    PERSONAL: Crea préstamo directo.
    """
    libros = [l for l in Libro.objects.all() if l.disponibles > 0] 
    es_personal = es_bibliotecario(request.user)
    usuarios = User.objects.all() if es_personal else [request.user]
    
    # Soporte para pre-seleccionar libro desde el catálogo
    libro_seleccionado_id = request.GET.get('libro_id')
    
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        usuario_id = request.POST.get('usuario') if es_personal else request.user.id
        libro = get_object_or_404(Libro, id=libro_id)
        usuario = get_object_or_404(User, id=usuario_id)
        
        # Bloqueo morosos
        tiene_multas = Multa.objects.filter(prestamo__usuario=usuario, pagada=False).exists()
        if tiene_multas:
            return HttpResponseForbidden("Usuario con multas pendientes.")
            
        estado = 'prestado' if es_personal else 'solicitado'
        prestamo = Prestamos.objects.create(
            libro=libro, usuario=usuario, 
            fecha=timezone.now().date(), 
            fecha_max=timezone.now().date() + timezone.timedelta(days=7),
            estado=estado
        )
        
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_prestamo',
            descripcion=f"Préstamo {prestamo.codigo} para {usuario.username} (Estado: {estado})",
            prestamo_id=prestamo.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return redirect('lista_prestamos')
        
    return render(request, 'crear_prestamo.html', {
        'libros': libros, 
        'usuarios': usuarios, 
        'es_personal': es_personal,
        'libro_preseleccionado': int(libro_seleccionado_id) if libro_seleccionado_id else None,
        'fecha': timezone.now().date().isoformat()
    })

@user_passes_test(es_bibliotecario)
@login_required
def aceptar_solicitud(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if prestamo.confirmar():
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_prestamo',
            descripcion=f"Aceptada solicitud {prestamo.codigo}",
            prestamo_id=prestamo.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
    return redirect('lista_prestamos')

@user_passes_test(es_bibliotecario)
@login_required
def rechazar_solicitud(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if prestamo.rechazar():
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_prestamo',
            descripcion=f"Rechazada solicitud {prestamo.codigo}",
            prestamo_id=prestamo.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
    return redirect('lista_prestamos')

@user_passes_test(es_bibliotecario)
@login_required
def finalizar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if request.method == 'POST':
        tipo = request.POST.get('tipo_dano')
        monto = request.POST.get('monto_dano', 0)
        prestamo.finalizar(tipo_multa=tipo, monto_multa=monto)
        
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='finalizar_prestamo',
            descripcion=f"Devolución {prestamo.codigo}",
            prestamo_id=prestamo.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
    return redirect('lista_prestamos')

@user_passes_test(es_bibliotecario)
@login_required
def renovar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if prestamo.renovar():
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_prestamo', # Podria ser 'renovar'
            descripcion=f"Renovación {prestamo.codigo}",
            prestamo_id=prestamo.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
    return redirect('lista_prestamos')

# --- SECCION MULTAS ---

@login_required
def lista_multas(request):
    if es_bibliotecario(request.user):
        multas = Multa.objects.all().order_by('-fecha')
    else:
        multas = Multa.objects.filter(prestamo__usuario=request.user).order_by('-fecha')
    return render(request, 'multas.html', {'multas': multas})

@login_required
def pagar_multa(request, id):
    multa = get_object_or_404(Multa, id=id)
    if request.method == 'POST':
        if multa.pagar(usuario_cajero=request.user):
            RegistroAuditoria.objects.create(
                usuario=request.user,
                accion='pagar_multa',
                descripcion=f"Pago multa {multa.codigo}",
                multa_id=multa.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
    return redirect('lista_multa')

# --- SECCION ADMIN ---

@user_passes_test(es_admin)
@login_required
def panel_administracion(request):
    audit_logs = RegistroAuditoria.objects.all().order_by('-fecha_hora')[:100]
    usuarios = User.objects.all()
    context = {
        'audit_logs': audit_logs,
        'usuarios': usuarios,
    }
    return render(request, 'admin_panel.html', context)

@user_passes_test(es_admin)
@login_required
def crear_empleado(request):
    from django.contrib.auth.models import Group
    grupos = Group.objects.exclude(name='Cliente')
    if request.method == 'POST':
        username = request.POST.get('username')
        passw = request.POST.get('password')
        email = request.POST.get('email')
        grupo_id = request.POST.get('grupo')
        
        user = User.objects.create_user(username=username, password=passw, email=email)
        grupo = Group.objects.get(id=grupo_id)
        user.groups.add(grupo)
        
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_usuario',
            descripcion=f"Admin creó empleado {username} como {grupo.name}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return redirect('panel_administracion')
    return render(request, 'crear_empleado.html', {'grupos': grupos})

@login_required
def lista_usuarios(request):
    if not es_bibliotecario(request.user):
        return HttpResponseForbidden()
    usuarios = User.objects.all()
    return render(request, 'usuarios.html', {'usuarios': usuarios})

@login_required
def detalle_usuario(request, id):
    if not es_bibliotecario(request.user) and request.user.id != id:
        return HttpResponseForbidden()
    usuario = get_object_or_404(User, id=id)
    prestamos = Prestamos.objects.filter(usuario=usuario).order_by('-fecha')
    pendientes = prestamos.filter(fecha_devolucion__isnull=True).count()
    return render(request, 'detalle_usuario.html', {
        'usuario': usuario,
        'prestamos': prestamos,
        'pendientes_count': pendientes
    })

# --- SECCION REGISTRO Y AUTH ---

def registro(request):
    from .forms import FormularioRegistroExtendido
    from django.contrib.auth.models import Group
    if request.method == 'POST':
        form = FormularioRegistroExtendido(request.POST)
        if form.is_valid():
            usuario = form.save()
            grupo_cliente, _ = Group.objects.get_or_create(name='Cliente')
            usuario.groups.add(grupo_cliente)
            
            RegistroAuditoria.objects.create(
                usuario=usuario,
                accion='crear_usuario',
                descripcion=f"Nuevo cliente registrado: {usuario.username}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            login(request, usuario)
            return redirect('index')
    else:
        form = FormularioRegistroExtendido()
    return render(request, 'registration/registro.html', {'form': form})

# --- SECCION API Y OTROS ---
@login_required
def buscar_libro_api(request):
    from .forms import FormularioBusquedaLibro
    from .services import ClienteOpenLibrary
    resultado = None
    resultados_busqueda = []
    if request.method == 'POST':
        form = FormularioBusquedaLibro(request.POST)
        if form.is_valid():
            cliente = ClienteOpenLibrary()
            isbn = form.cleaned_data.get('codigo_isbn')
            termino = form.cleaned_data.get('termino_busqueda')
            if isbn:
                libro_data = cliente.obtener_libro_por_isbn(isbn)
                if libro_data:
                    resultado = {
                        'titulo': libro_data.get('title'),
                        'autores': libro_data.get('authors', [{'name': 'Desconocido'}]), 
                        'cover_url': cliente.obtener_url_portada_isbn(isbn, 'M'),
                        'isbn': isbn,
                    }
            elif termino:
                docs = cliente.buscar_libros(termino)
                for doc in docs:
                    resultados_busqueda.append({
                        'titulo': doc.get('title'),
                        'autor': doc.get('author_name', ['Desconocido'])[0],
                        'isbn': doc.get('isbn', [''])[0],
                    })
    else:
        form = FormularioBusquedaLibro()
    return render(request, 'buscar_libro_api.html', {'form': form, 'resultado': resultado, 'resultados_busqueda': resultados_busqueda})

@login_required
def guardar_libro_api(request):
    if not es_bodeguero(request.user):
        return HttpResponseForbidden()
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        nombre_autor = request.POST.get('autor')
        isbn = request.POST.get('isbn')
        cover_url = request.POST.get('cover_url')
        
        partes = nombre_autor.split(' ')
        nombre = " ".join(partes[:-1]) if len(partes) > 1 else nombre_autor
        apellido = partes[-1] if len(partes) > 1 else ""
        autor, _ = Autor.objects.get_or_create(nombre__iexact=nombre, apellido__iexact=apellido, defaults={'nombre': nombre, 'apellido': apellido})
        
        libro = Libro.objects.create(titulo=titulo, autor=autor, isbn=isbn, stock=1)
        if cover_url and cover_url != 'None':
             try:
                resp = requests.get(cover_url)
                if resp.status_code == 200:
                    libro.imagen.save(f"{isbn}.jpg", ContentFile(resp.content), save=True)
             except: pass
        return redirect('lista_libros')
    return redirect('buscar_libro_api')

# Reportes PDF (Importados desde reportes.py usualmente)
from .reportes import generar_reporte_auditoria_pdf, generar_reporte_multas_pdf
