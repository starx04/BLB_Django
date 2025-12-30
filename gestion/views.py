from django.shortcuts import render,redirect ,get_object_or_404
import requests
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from django.conf import settings 
from django.http import HttpResponseForbidden
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from .models import Libro, Prestamos, Multa, Autor

def index(request):
    titulo2 = "Hola Mundo"
    title = settings.TITLE
    return render(request, 'home.html', {'titulo': title, "t": titulo2})
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
                    import requests
                    from django.core.files.base import ContentFile
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
    
#--SECCION PRESTAMOS--
@login_required
def lista_prestamos(request):
    prestamos = Prestamos.objects.all()
    return render(request, 'prestamos.html', {'prestamos': prestamos})

@login_required
def crear_prestamo(request):
    if not request.user.has_perm('gestion.ver_prestamos'):
        return HttpResponseForbidden()
    libros = [l for l in Libro.objects.all() if l.disponibles > 0] 
    usuarios = User.objects.all()
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        usuario_id = request.POST.get('usuario')
        fecha_prestamo = request.POST.get('fecha_prestamo')
        if libro_id and usuario_id and fecha_prestamo:
            libro = get_object_or_404(Libro, id=libro_id)
            if libro.disponibles < 1:
                return HttpResponseForbidden("No hay copias disponibles")

            usuario = get_object_or_404(User, id=usuario_id)
            
            # BLOQUEO MOROSOS
            # 1. Chequear multas impagas indirectamente a traves de sus prestamos
            prestamos_usuario = Prestamos.objects.filter(usuario=usuario)
            tiene_multas = Multa.objects.filter(prestamo__in=prestamos_usuario, pagada=False).exists()
            
            # 2. Chequear prestamos vencidos
            tiene_vencidos = prestamos_usuario.filter(estado='vencido').exists()
            
            if tiene_multas or tiene_vencidos:
                 return HttpResponseForbidden(f"El usuario {usuario.username} tiene multas pendientes o libros vencidos. No se puede realizar el prestamo.")
            prestamo = Prestamos.objects.create(libro=libro, 
                                                usuario=usuario, 
                                                fecha_prestamo=fecha_prestamo)
            # No necesitamos cambiar libro.disponible = False manualmente
            # La propiedad .disponibles lo calcula solo
            return redirect('lista_prestamos')
    fecha=(timezone.now().date()).isoformat()        
    return render(request, 'crear_prestamo.html', {'libros': libros,
                                                                    'usuarios': usuarios,
                                                                    'fecha': fecha})

@login_required
def finalizar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if request.method == 'POST':
        prestamo.finalizar()
    return redirect('lista_prestamos')

@login_required
def renovar_prestamo(request, id):
    prestamo = get_object_or_404(Prestamos, id=id)
    if request.method == 'POST':
        prestamo.renovar()
    return redirect('lista_prestamos')

@login_required
def detalle_prestamo(request):
    pass

#--SECCION MULTAS--
@login_required
def lista_multas(request):
    multas = Multa.objects.all()
    return render(request, 'multas.html', {'multas': multas})

@login_required
def crear_multa(request):
    pass
@login_required
def detalle_multa(request):
    pass
#--SECCION USUARIOS--
@login_required
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'usuarios.html', {'usuarios': usuarios})

@login_required
def crear_usuario(request):
    pass
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
    if request.method == 'POST':
        form = FormularioRegistroExtendido(request.POST) # Formulario extendido
        if form.is_valid():
            usuario = form.save()
            try:
                permiso = Permission.objects.get(codename='gestionar_prestamos', content_type__app_label='gestion')
                usuario.user_permissions.add(permiso)
            except Permission.DoesNotExist:
                pass 
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
from .forms import FormularioBusquedaLibro

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
                    from django.core.files.base import ContentFile
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
