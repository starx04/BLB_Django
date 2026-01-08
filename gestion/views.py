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

from .models import Libro, Prestamos, Multa, Autor, RegistroAuditoria, PerfilUsuario
from django.contrib import messages
from django.db.models import Q, Count, Sum

# --- DECORADORES DE ROLES ---
def es_cliente(user):
    return user.groups.filter(name='Cliente').exists()

def es_admin(user):
    return user.is_superuser or user.groups.filter(name='Administrador').exists()

def es_personal_biblioteca(user):
    """Bibliotecarios, Admin y Superusers"""
    return user.is_superuser or user.groups.filter(name__in=['Bibliotecario', 'Administrador']).exists()

def es_personal_bodega(user):
    """Bodegueros, Admin y Superusers"""
    return user.is_superuser or user.groups.filter(name__in=['Bodeguero', 'Administrador']).exists()

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

@user_passes_test(es_personal_bodega)
@login_required
def crear_libros(request, id=None):
    from .models import Categoria
    libro_obj = get_object_or_404(Libro, id=id) if id else None
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        nombre_autor_texto = request.POST.get('autor_texto')
        isbn = request.POST.get('isbn')
        stock_raw = request.POST.get('stock')
        
        # VALIDACIÓN DE STOCK
        if not stock_raw or int(stock_raw) <= 0:
            messages.error(request, "Error: Debes ingresar un stock válido de libros (mínimo 1).")
            return render(request, 'crear_libros.html', {
                'autores': autores, 
                'categorias': categorias,
                'error_stock': True,
                'prefill': request.POST
            })
            
        stock = int(stock_raw)
        nombre = nombre_autor_texto.strip()
        partes = nombre.split(' ')
        nombre_nuevo = " ".join(partes[:-1]) if len(partes) > 1 else nombre
        apellido_nuevo = partes[-1] if len(partes) > 1 else ""
        
        imagen = request.FILES.get('imagen')
        cover_url = request.POST.get('cover_url')
        
        autor_final, _ = Autor.objects.get_or_create(
            nombre__iexact=nombre_nuevo, 
            apellido__iexact=apellido_nuevo, 
            defaults={'nombre': nombre_nuevo, 'apellido': apellido_nuevo}
        )
        
        if libro_obj:
            libro_obj.titulo = titulo
            libro_obj.autor = autor_final
            libro_obj.stock = stock
            libro_obj.isbn = isbn
            if imagen: libro_obj.imagen = imagen
            libro_obj.save()
            nuevo_libro = libro_obj
        else:
            nuevo_libro = Libro.objects.create(
                titulo=titulo, 
                autor=autor_final, 
                stock=stock, 
                isbn=isbn,
                imagen=imagen
            )

        # Categoria (ManyToMany)
        categoria_id = request.POST.get('categoria')
        if categoria_id:
            from .models import Categoria
            categoria_obj = Categoria.objects.get(id=categoria_id)
            nuevo_libro.categorias.set([categoria_obj])

        # Lógica de descarga de imagen API...
        if not imagen and cover_url and cover_url.startswith('http'):
            try:
                if cover_url.startswith('http:'):
                    cover_url = cover_url.replace('http:', 'https:')
                headers = {'User-Agent': 'GestionBiblioteca/1.0'}
                response = requests.get(cover_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    from django.core.files.base import ContentFile
                    extension = cover_url.split('.')[-1].split('?')[0]
                    if len(extension) > 4 or '/' in extension: extension = 'jpg'
                    file_name = f"libro_{nuevo_libro.id}.{extension}"
                    nuevo_libro.imagen.save(file_name, ContentFile(response.content), save=True)
            except Exception as e:
                print(f"DEBUG: Error descargando portada: {str(e)}")
        
        RegistroAuditoria.objects.create(
            usuario=request.user, accion='crear_libro',
            descripcion=f"Libro '{titulo}' {'actualizado' if libro_obj else 'creado'} por {request.user.username}",
            libro_id=nuevo_libro.id, ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Libro '{titulo}' registrado exitosamente.")
        return redirect('lista_libros')

    # GET: Pre-llenado (Edición o API)
    prefill = {}
    if libro_obj: # Datos de edición
        prefill = {
            'titulo': libro_obj.titulo,
            'autor_texto': f"{libro_obj.autor.nombre} {libro_obj.autor.apellido}",
            'isbn': libro_obj.isbn,
            'stock': libro_obj.stock,
            'categoria': libro_obj.categorias.first().id if libro_obj.categorias.exists() else '',
            'bibliografia': libro_obj.bibliografia,
            'is_api': False 
        }
    elif 'titulo' in request.GET: # Datos de API
        prefill = {
            'titulo': request.GET.get('titulo', ''),
            'autor_texto': request.GET.get('autor', ''),
            'isbn': request.GET.get('isbn', ''),
            'cover_url': request.GET.get('cover_url', ''),
            'is_api': True
        }
        
    return render(request, 'crear_libros.html', {
        'autores': autores, 
        'categorias': categorias, 
        'prefill': prefill,
        'libro_obj': libro_obj
    })

@user_passes_test(es_personal_bodega)
@login_required
def crear_autor(request, id=None):
    autor = get_object_or_404(Autor, id=id) if id else None
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')

        if autor:
            autor.nombre = nombre
            autor.apellido = apellido
            autor.bibliografia = bibliografia
            autor.save()
        else:
            Autor.objects.create(
                nombre=nombre, 
                apellido=apellido, 
                bibliografia=bibliografia
            )
        return redirect('lista_autores')
    return render(request, 'crear_autor.html', {'autor': autor, 'mode': 'Editar' if id else 'Nuevo'})

# --- SECCION PRESTAMOS ---

@login_required
def lista_prestamos(request):
    """
    CLIENTE: Ve solo sus préstamos.
    PERSONAL: Ve todos.
    """
    if es_personal_biblioteca(request.user):
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
    es_personal = es_personal_biblioteca(request.user)
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
        fecha_form = request.POST.get('fecha_prestamo', timezone.now().date())
        dias_prestamo = getattr(settings, 'DIAS_PRESTAMO', 7)
        
        prestamo = Prestamos.objects.create(
            libro=libro, usuario=usuario, 
            fecha=fecha_form, 
            fecha_max=None, # Dejamos que el model.save() lo calcule solo
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

@user_passes_test(es_personal_biblioteca)
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

@user_passes_test(es_personal_biblioteca)
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

@user_passes_test(es_personal_biblioteca)
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

@user_passes_test(es_personal_biblioteca)
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
    if es_personal_biblioteca(request.user):
        multas = Multa.objects.all().order_by('-fecha')
    else:
        multas = Multa.objects.filter(prestamo__usuario=request.user).order_by('-fecha')
    return render(request, 'multas.html', {'multas': multas})



@login_required
def pagar_multa(request, id):
    multa = get_object_or_404(Multa, id=id)
    if request.method == 'POST':
        if multa.pagar(usuario_cajero=request.user):
            messages.success(request, f"Pago exitoso: Multa {multa.codigo} registrada.")
            RegistroAuditoria.objects.create(
                usuario=request.user,
                accion='pagar_multa',
                descripcion=f"Pago multa {multa.codigo}",
                multa_id=multa.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
        else:
            messages.error(request, "Esta multa ya ha sido pagada previamente.")
    return redirect('lista_multa')

@user_passes_test(es_personal_biblioteca)
@login_required
def editar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    libros = Libro.objects.all()
    usuarios = User.objects.all()
    
    if request.method == 'POST':
        prestamo.libro = get_object_or_404(Libro, id=request.POST.get('libro'))
        prestamo.usuario = get_object_or_404(User, id=request.POST.get('usuario'))
        prestamo.fecha = request.POST.get('fecha')
        prestamo.fecha_max = request.POST.get('fecha_max')
        prestamo.estado = request.POST.get('estado')
        prestamo.save()
        messages.success(request, f"Préstamo {prestamo.codigo} actualizado.")
        return redirect('lista_prestamos')
        
    return render(request, 'editar_prestamo.html', {'prestamo': prestamo, 'libros': libros, 'usuarios': usuarios})

@user_passes_test(es_personal_biblioteca)
@login_required
def editar_multa(request, id):
    multa = get_object_or_404(Multa, id=id)
    
    # Validación de multa pagada (solo admin/super permite editar si ya pagó)
    if multa.pagada and not (request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()):
        messages.error(request, "No puedes editar una multa que ya ha sido pagada.")
        return redirect('lista_multa')

    if request.method == 'POST':
        multa.tipo = request.POST.get('tipo')
        multa.monto = request.POST.get('monto')
        multa.pagada = 'pagada' in request.POST
        # Si se marca como pagada manualmente, registramos quién lo hizo
        if multa.pagada and not multa.fecha_pago:
            multa.fecha_pago = timezone.now()
            multa.pagada_por = request.user
        
        # Guardamos usando force_admin=True si es admin para saltar el bloqueo del model.save()
        multa.save(force_admin=es_admin(request.user))
        
        messages.success(request, f"Multa {multa.codigo} actualizada.")
        return redirect('lista_multa')
        
    return render(request, 'editar_multa.html', {'multa': multa})

# --- SECCION ADMIN ---

@user_passes_test(es_admin)
@login_required
def panel_administracion(request):
    audit_logs = RegistroAuditoria.objects.all().order_by('-fecha_hora')[:15]
    total_personal = User.objects.exclude(groups__name='Cliente').count()
    total_clientes = User.objects.filter(groups__name='Cliente').count()
    
    context = {
        'audit_logs': audit_logs,
        'total_personal': total_personal,
        'total_clientes': total_clientes,
    }
    return render(request, 'admin_panel.html', context)

@user_passes_test(es_admin)
@login_required
def ver_logs(request):
    """Vista detallada de todos los logs del sistema."""
    logs = RegistroAuditoria.objects.all().order_by('-fecha_hora')
    
    # Filtros opcionales
    accion = request.GET.get('accion')
    usuario = request.GET.get('usuario')
    
    if accion:
        logs = logs.filter(accion=accion)
    if usuario:
        logs = logs.filter(usuario__username__icontains=usuario)
        
    context = {
        'logs': logs,
        'acciones': RegistroAuditoria.ACCIONES,
    }
    return render(request, 'logs.html', context)

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
        messages.success(request, f"Empleado {username} creado exitosamente.")
        return redirect('lista_personal')
    return render(request, 'crear_empleado.html', {'grupos': grupos})

@user_passes_test(es_admin)
@login_required
def lista_personal(request):
    # Personal: Administrador, Bibliotecario, Bodeguero o Superusuarios
    personal = User.objects.filter(
        Q(groups__name__in=['Administrador', 'Bibliotecario', 'Bodeguero']) | Q(is_superuser=True)
    ).distinct().order_by('username')
    return render(request, 'lista_personal.html', {'personal': personal})

@login_required
def lista_clientes(request):
    # Clientes lo puede ver el bibliotecario y el admin
    if not (es_admin(request.user) or es_personal_biblioteca(request.user)):
        return HttpResponseForbidden()
    
    # Clientes: Únicamente los que tienen el rol de Cliente y NO son personal
    clientes = User.objects.filter(groups__name='Cliente').exclude(
        Q(groups__name__in=['Administrador', 'Bibliotecario', 'Bodeguero']) | Q(is_superuser=True)
    ).annotate(
        multas_pendientes_count=Count('Prestamos__Multa', filter=Q(Prestamos__Multa__pagada=False))
    ).distinct().order_by('username')
    
    return render(request, 'lista_clientes.html', {'clientes': clientes})

@user_passes_test(es_admin)
@login_required
def editar_usuario(request, id):
    usuario_obj = get_object_or_404(User, id=id)
    # Importar el formulario aquí o al inicio
    from .forms import FormularioEdicionUsuario
    
    if request.method == 'POST':
        form = FormularioEdicionUsuario(request.POST, instance=usuario_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"Datos del usuario {usuario_obj.username} actualizados correctamente.")
            # Redirigir según el rol
            if usuario_obj.groups.filter(name='Cliente').exists() and not usuario_obj.groups.filter(name__in=['Administrador', 'Bibliotecario', 'Bodeguero']).exists():
                return redirect('lista_clientes')
            return redirect('lista_personal')
    else:
        form = FormularioEdicionUsuario(instance=usuario_obj)
    
    return render(request, 'editar_usuario.html', {'form': form, 'usuario_obj': usuario_obj})

@user_passes_test(es_admin)
@login_required
def eliminar_usuario(request, id):
    if request.method != 'POST':
        return HttpResponseForbidden("Acción no permitida vía GET.")
        
    usuario_a_eliminar = get_object_or_404(User, id=id)
    
    if usuario_a_eliminar.is_superuser:
        messages.error(request, "No se puede eliminar a un superusuario.")
        return redirect('panel_administracion')
        
    username = usuario_a_eliminar.username
    usuario_a_eliminar.delete()
    
    RegistroAuditoria.objects.create(
        usuario=request.user,
        accion='crear_usuario', # Reusando accion existente para logs de usuarios
        descripcion=f"Admin eliminó al usuario: {username}",
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, f"Usuario {username} eliminado correctamente.")
    return redirect('panel_administracion')

@login_required
def lista_usuarios(request):
    if not es_personal_biblioteca(request.user):
        return HttpResponseForbidden()
    usuarios = User.objects.all()
    return render(request, 'usuarios.html', {'usuarios': usuarios})

@login_required
def detalle_usuario(request, id):
    if not es_personal_biblioteca(request.user) and request.user.id != id:
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
                    # En OpenLibrary data API, la portada suele estar en .cover['medium']
                    cover_from_api = None
                    if 'cover' in libro_data:
                        cover_from_api = libro_data['cover'].get('medium') or libro_data['cover'].get('large')
                    
                    resultado = {
                        'titulo': libro_data.get('title'),
                        'autores': libro_data.get('authors', [{'name': 'Desconocido'}]), 
                        'cover_url': cover_from_api or cliente.obtener_url_portada_isbn(isbn, 'M'),
                        'isbn': isbn,
                        'paginas': libro_data.get('number_of_pages', 'N/A'),
                        'anio': libro_data.get('publish_date', 'N/A'),
                    }
            elif termino:
                docs = cliente.buscar_libros(termino)
                for doc in docs:
                    # Intentamos obtener un ISBN válido (el primero de la lista)
                    isbns = doc.get('isbn', [])
                    isbn_valido = isbns[0] if isbns else ""
                    
                    # Intentamos obtener la URL de la portada
                    cover_id = doc.get('cover_i')
                    if cover_id:
                        url_img = cliente.obtener_url_portada(cover_id, 'M')
                    elif isbn_valido:
                        url_img = cliente.obtener_url_portada_isbn(isbn_valido, 'M')
                    else:
                        url_img = None

                    resultados_busqueda.append({
                        'titulo': doc.get('title'),
                        'autor': doc.get('author_name', ['Desconocido'])[0],
                        'isbn': isbn_valido,
                        'anio': doc.get('first_publish_year', 'N/A'),
                        'cover_url': url_img,
                    })
    else:
        form = FormularioBusquedaLibro()
    return render(request, 'buscar_libro_api.html', {'form': form, 'resultado': resultado, 'resultados_busqueda': resultados_busqueda})

@login_required
def guardar_libro_api(request):
    """
    Ahora no guarda directamente, sino que redirecciona al formulario 
    de creación con los datos pre-cargados para confirmación.
    """
    if not es_personal_bodega(request.user):
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '')
        autor = request.POST.get('autor', '')
        isbn = request.POST.get('isbn', '')
        cover_url = request.POST.get('cover_url', '')
        
        from django.utils.http import urlencode
        from django.urls import reverse
        params = urlencode({
            'titulo': titulo,
            'autor': autor,
            'isbn': isbn,
            'cover_url': cover_url
        })
        return redirect(f"{reverse('crear_libros')}?{params}")
    
    return redirect('buscar_libro_api')

# Reportes PDF (Importados desde reportes.py usualmente)
from .reportes import generar_reporte_auditoria_pdf, generar_reporte_multas_pdf
