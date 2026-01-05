from django.shortcuts import render,redirect ,get_object_or_404
import requests
from django.contrib.auth.decorators import login_required
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

from django.contrib.auth.decorators import user_passes_test

def index(request):
    """Vista pública del Dashboard - No requiere login."""
    title = settings.TITLE
    
    # KPIs del Dashboard
    total_libros = Libro.objects.count()
    prestamos_activos = Prestamos.objects.filter(estado='prestado').count()
    multas_pendientes = Multa.objects.filter(pagada=False).aggregate(total=Sum('monto'))['total'] or 0
    usuarios_registrados = User.objects.count()
    
    # Datos para tabla de recientes (Últimos 5 libros agregados)
    # Asumimos que ID más alto es más reciente ya que no tenemos 'created_at'
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
#-- SECCION LIBROS --
@login_required
def lista_libros(request):
    libros = Libro.objects.all()
    return render(request, 'libros.html', {'libros': libros})

@login_required
def crear_libros(request):
    autores = Autor.objects.all()
    categorias = Categoria.objects.all()
    
    if request.method == 'POST':
        # Recogemos datos del formulario
        titulo = request.POST.get('titulo')
        nombre_autor_texto = request.POST.get('autor_texto')
        autor_id_select = request.POST.get('autor_select') # Por si acaso se restableciera el select
        isbn = request.POST.get('isbn')
        cover_url = request.POST.get('cover_url')
        bibliografia = request.POST.get('bibliografia')
        imagen = request.FILES.get('imagen')
        disponible = request.POST.get('disponible') == 'on'
        confirmar_duplicado = request.POST.get('confirmar_duplicado') == 'true'

        # 1. VERIFICACIÓN DE DUPLICADO
        # Si NO ha confirmado aún y el ISBN ya existe...
        if isbn and Libro.objects.filter(isbn=isbn).exists() and not confirmar_duplicado:
            libro_existente = Libro.objects.filter(isbn=isbn).first()
            context = {
                'autores': autores,
                'advertencia_duplicado': True,
                'isbn_duplicado': isbn,
                'titulo_existente': libro_existente.titulo,
                # Pasamos los valores de vuelta para que no se pierdan en el formulario
                'request': request 
            }
            return render(request, 'crear_libros.html', context)

        # 2. LOGICA DE GUARDADO (Si no hay duplicado O el usuario confirmó)
        if titulo and (nombre_autor_texto or autor_id_select):
            
            # Gestionar Autor: Preferencia al texto escrito, si no buscar coincidencia
            autor_final = None
            
            # Intentamos parsear el nombre escrito
            nombre = nombre_autor_texto.strip()
            partes = nombre.split(' ')
            if len(partes) > 1:
                apellido_nuevo = partes[-1]
                nombre_nuevo = " ".join(partes[:-1])
            else:
                nombre_nuevo = nombre
                apellido_nuevo = ""
                
            # Buscamos si existe un autor asi (case insensitive)
            autor_existente = Autor.objects.filter(nombre__iexact=nombre_nuevo, apellido__iexact=apellido_nuevo).first()
            
            if autor_existente:
                autor_final = autor_existente
            else:
                # CREAR NUEVO AUTOR AUTOMATICAMENTE
                autor_final = Autor.objects.create(nombre=nombre_nuevo, apellido=apellido_nuevo)

            # Crear el Libro
            nuevo_libro = Libro(
                titulo=titulo,
                autor=autor_final,
                stock=int(request.POST.get('stock', 1)),

                bibliografia=bibliografia,
                isbn=isbn
            )
            
            # Manejo de Categorias
            categoria_id = request.POST.get('categoria')
            
            # Guardamos primero para tener ID para M2M
            # (El resto del manejo de imagen y guardado sigue igual,
            # solo necesitamos guardar M2M despues del save())

            if imagen:
                nuevo_libro.imagen = imagen
            elif cover_url and cover_url != 'None':
                 try:
                    response = requests.get(cover_url)
                    if response.status_code == 200:
                        nuevo_libro.imagen.save(f"{isbn or titulo}.jpg", ContentFile(response.content), save=False)
                 except Exception:
                    pass # Si falla la imagen, guardamos el libro igual sin ella
            
            try:
                nuevo_libro.save()
                if categoria_id:
                    cat = Categoria.objects.get(id=categoria_id)
                    nuevo_libro.categorias.add(cat)
                return redirect('lista_libros')
            except Exception as e:
                # En caso de error de BD, mostrar en el form (aunque unique=True saltaria en save())
                pass 

    return render(request, 'crear_libros.html', {'autores': autores, 'categorias': categorias})
#-- SECCION AUTORES --
@login_required
def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'autores.html', {'autores': autores})

@login_required
def crear_autor(request,id=None):
    if id == None:
        autor = None
        mode = "Nuevo"
    else:
        autor = get_object_or_404(Autor, id=id)
        mode = "Editar"
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        imagen = request.FILES.get('imagen')
        
        if autor == None:
            Autor.objects.create(nombre=nombre, apellido=apellido,
                                 bibliografia=bibliografia, imagen=imagen )
        else:
            autor.nombre = nombre
            autor.apellido = apellido
            autor.bibliografia = bibliografia
            if imagen:
                autor.imagen = imagen
            autor.save()
        return redirect('lista_autores')
        
    context = {
        'autor': autor,
        'titulo': 'Editar Autor' if mode == 'Editar' else 'Crear Autor',
        'texto_boton': 'Guardar cambios' if mode == 'Editar' else 'Crear Autor', 
        'mode': mode
    }
    return render(request, 'crear_autor.html', context)
    
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
        
        # Lógica simplificada de creación para brevedad en esta actualización
        nombre = nombre_autor_texto.strip()
        partes = nombre.split(' ')
        nombre_nuevo = " ".join(partes[:-1]) if len(partes) > 1 else nombre
        apellido_nuevo = partes[-1] if len(partes) > 1 else ""
        
        autor_final, _ = Autor.objects.get_or_create(nombre__iexact=nombre_nuevo, apellido__iexact=apellido_nuevo, defaults={'nombre': nombre_nuevo, 'apellido': apellido_nuevo})
        
        nuevo_libro = Libro.objects.create(titulo=titulo, autor=autor_final, stock=int(stock), isbn=isbn)
        
        # [AUDITORIA]
        RegistroAuditoria.objects.create(
            usuario=request.user,
            accion='crear_libro',
            descripcion=f"Bodeguero creó libro: {titulo}",
            libro_id=nuevo_libro.id,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return redirect('lista_libros')
    return render(request, 'crear_libros.html', {'autores': autores, 'categorias': categorias})

#-- SECCION AUTORES --
@login_required
def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'autores.html', {'autores': autores})

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

#-- SECCION ADMIN --
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

#-- SECCION PRESTAMOS --
@login_required
def lista_prestamos(request):
    if es_bibliotecario(request.user):
        prestamos = Prestamos.objects.all().order_by('-fecha')
    else:
        prestamos = Prestamos.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'prestamos.html', {'prestamos': prestamos})

@login_required
def crear_prestamo(request):
    libros = [l for l in Libro.objects.all() if l.disponibles > 0] 
    es_personal = es_bibliotecario(request.user)
    usuarios = User.objects.all() if es_personal else [request.user]
    
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        usuario_id = request.POST.get('usuario') if es_personal else request.user.id
        fecha_str = request.POST.get('fecha_prestamo')
        
        fecha_prestamo = timezone.now().date() # Por defecto hoy
        libro = get_object_or_404(Libro, id=libro_id)
        usuario = get_object_or_404(User, id=usuario_id)
        
        # Bloqueo morosos
        tiene_multas = Multa.objects.filter(prestamo__usuario=usuario, pagada=False).exists()
        if tiene_multas:
            return HttpResponseForbidden("Usuario con multas pendientes.")
            
        estado = 'prestado' if es_personal else 'solicitado'
        prestamo = Prestamos.objects.create(
            libro=libro, usuario=usuario, 
            fecha=fecha_prestamo, 
            fecha_max=fecha_prestamo + timezone.timedelta(days=7),
            estado=estado
        )
        return redirect('lista_prestamos')
    return render(request, 'crear_prestamo.html', {'libros': libros, 'usuarios': usuarios, 'es_personal': es_personal})

@user_passes_test(es_bibliotecario)
@login_required
def aceptar_solicitud(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    prestamo.confirmar()
    return redirect('lista_prestamos')

@user_passes_test(es_bibliotecario)
@login_required
def rechazar_solicitud(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    prestamo.rechazar()
    return redirect('lista_prestamos')

@user_passes_test(es_bibliotecario)
@login_required
def finalizar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if request.method == 'POST':
        tipo = request.POST.get('tipo_dano')
        monto = request.POST.get('monto_dano', 0)
        prestamo.finalizar(tipo_multa=tipo, monto_multa=monto)
    return redirect('lista_prestamos')

@user_passes_test(es_bibliotecario)
@login_required
def renovar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    prestamo.renovar()
    return redirect('lista_prestamos')




#--SECCION MULTAS--
@login_required
def lista_multas(request):
    multas = Multa.objects.all().order_by('-fecha')
    return render(request, 'multas.html', {'multas': multas})

@login_required
def pagar_multa(request, id):
    """
    Procesa el pago simulado de una multa.
    Registra quién procesó el pago para auditoría.
    """
    multa = get_object_or_404(Multa, id=id)
    if request.method == 'POST':
        if multa.pagar(usuario_cajero=request.user):
            # [AUDITORÍA] Registrar pago
            RegistroAuditoria.objects.create(
                usuario=request.user,
                accion='pagar_multa',
                descripcion=f"Pago de multa {multa.codigo} - ${multa.monto} - Usuario: {multa.prestamo.usuario.username}",
                multa_id=multa.id,
                ip_address=request.META.get('REMOTE_ADDR')
            )
    return redirect('lista_multa')


#--SECCION USUARIOS--
@login_required
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'usuarios.html', {'usuarios': usuarios})


@login_required
def detalle_usuario(request, id):
    usuario = get_object_or_404(User, id=id)
    prestamos = Prestamos.objects.filter(usuario=usuario).order_by('-fecha')
    
    # Contamos cuantos no han sido devueltos (no tienen fecha de devolucion)
    pendientes = prestamos.filter(fecha_devolucion__isnull=True).count()
    
    return render(request, 'detalle_usuario.html', {
        'usuario': usuario,
        'prestamos': prestamos,
        'pendientes_count': pendientes
    })

from .forms import FormularioBusquedaLibro, FormularioRegistroExtendido

#--SECCION REGISTRO--
def registro(request):
    from django.contrib.auth.models import Group
    if request.method == 'POST':
        form = FormularioRegistroExtendido(request.POST)
        if form.is_valid():
            usuario = form.save()
            # Asignar automáticamente al grupo 'Cliente'
            grupo_cliente, _ = Group.objects.get_or_create(name='Cliente')
            usuario.groups.add(grupo_cliente)
            
            # [AUDITORIA]
            RegistroAuditoria.objects.create(
                usuario=usuario,
                accion='crear_usuario',
                descripcion=f"Nuevo cliente se registró: {usuario.username}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            login(request, usuario)
            return redirect('index')
    else:
        form = FormularioRegistroExtendido()
    return render(request, 'registration/registro.html', {'form': form})

#create your views here
from django.views.generic import ListView , CreateView , UpdateView , DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin,  PermissionRequiredMixin
from django.urls import reverse_lazy
from .services import ClienteOpenLibrary


#--SECCION API--
@login_required
def buscar_libro_api(request):
    """
    Vista para buscar libros y autores usando OpenLibrary API.
    """
    resultado = None
    resultados_busqueda = []
    
    if request.method == 'POST':
        form = FormularioBusquedaLibro(request.POST)
        if form.is_valid():
            cliente = ClienteOpenLibrary()
            isbn = form.cleaned_data.get('codigo_isbn')
            termino = form.cleaned_data.get('termino_busqueda')
            
            if isbn:
                # Busqueda exacta por ISBN
                libro_data = cliente.obtener_libro_por_isbn(isbn)
                if libro_data:
                    # Normalizamos estructura
                    cover_url = None
                    if 'covers' in libro_data and libro_data['covers']:
                         id_portada = libro_data['covers'][0]
                         cover_url = cliente.obtener_url_portada(id_portada, 'M')
                    
                    if not cover_url:
                        cover_url = cliente.obtener_url_portada_isbn(isbn, 'M')

                    resultado = {
                        'titulo': libro_data.get('title'),
                        'autores': libro_data.get('authors', [{'name': 'Desconocido'}]), 
                        'cover_url': cover_url,
                        'isbn': isbn,
                        'paginas': libro_data.get('number_of_pages', 'N/A')
                    }
            elif termino:
                # Busqueda general
                docs = cliente.buscar_libros(termino)
                for doc in docs:
                    cover_i = doc.get('cover_i')
                    resultados_busqueda.append({
                        'titulo': doc.get('title'),
                        'autor': doc.get('author_name', ['Desconocido'])[0],
                        'anio': doc.get('first_publish_year', 'N/A'),
                        'isbn': doc.get('isbn', [''])[0],
                        'cover_url': cliente.obtener_url_portada(cover_i, 'S')
                    })
    else:
        form = FormularioBusquedaLibro()

    return render(request, 'gestion/templates/buscar_libro_api.html', {
        'form': form,
        'resultado': resultado,
        'resultados_busqueda': resultados_busqueda
    })

@login_required
def guardar_libro_api(request):
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        nombre_autor = request.POST.get('autor')
        isbn = request.POST.get('isbn')
        cover_url = request.POST.get('cover_url')

        if not titulo:
             return redirect('buscar_libro_api')

        # Buscar o crear autor
        # Dividimos nombre y apellido simple
        partes = nombre_autor.split(' ')
        if len(partes) > 1:
            apellido = partes[-1]
            nombre = " ".join(partes[:-1])
        else:
            nombre = nombre_autor
            apellido = ""
            
        autor, created = Autor.objects.get_or_create(
            nombre__iexact=nombre, 
            apellido__iexact=apellido,
            defaults={'nombre': nombre, 'apellido': apellido}
        )
        
        # Verificar si libro ya existe
        if Libro.objects.filter(isbn=isbn).exists():
             # Opcional: Avisar que ya existe
             return redirect('lista_libros')

        libro = Libro(
            titulo=titulo,
            autor=autor,
            isbn=isbn,
            stock=1 # Por defecto 1 al guardar desde API
        )

        if cover_url and cover_url != 'None':
            try:
                response = requests.get(cover_url)
                if response.status_code == 200:
                    libro.imagen.save(f"{isbn}.jpg", ContentFile(response.content), save=False)
            except Exception as e:
                print(f"Error descargando imagen: {e}")
        
        libro.save()
        return redirect('lista_libros')
    
    return redirect('buscar_libro_api')

class LibroListView(LoginRequiredMixin, ListView):
    model = Libro
    template_name = 'gestion/templates/libros_view.html'
    context_object_name = 'libros'
    paginate_by = 10

class LibroDetailView(LoginRequiredMixin, DetailView):
    model = Libro
    template_name = 'gestion/templates/detalle_libro.html'
    context_object_name = 'libro'

class LibroCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Libro
    fields = ['titulo', 'autor', 'isbn', 'stock', 'categorias', 'imagen', 'bibliografia']
    template_name = 'gestion/templates/crear_libro.html'
    success_url = reverse_lazy('libro_list')
    permission_required = 'gestion.add_libro'

class LibroUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Libro
    fields = ['titulo', 'autor']
    template_name = 'gestion/templates/editar_libro.html'
    success_url = reverse_lazy('libro_list')
    permission_required = 'gestion.change_libro'        

class LibroDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Libro
    template_name = 'gestion/templates/delete_libro.html'
    success_url = reverse_lazy('libro_list')
    permission_required = 'gestion.delete_libro'
