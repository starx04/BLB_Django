from django.shortcuts import render,redirect ,get_object_or_404
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
def lista_libros(request):
    libros = Libro.objects.all()
    return render(request, 'libros.html', {'libros': libros})

def crear_libros(request):
    autores = Autor.objects.all()
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        autor_id = request.POST.get('autor')
        disponible = request.POST.get('disponible')
        bibliografia = request.POST.get('bibliografia')
        if titulo and autor_id and disponible and bibliografia:
            autor = Autor.objects.get(id=autor_id)
            Libro.objects.create(titulo=titulo, autor=autor, disponible=disponible, bibliografia=bibliografia)
            return redirect('lista_libros')
    return render(request, 'crear_libros.html', {'autores': autores})
#-- SECCION AUTORES --
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
def lista_prestamos(request):
    prestamos = Prestamos.objects.all()
    return render(request, 'prestamos.html', {'prestamos': prestamos})

@login_required
def crear_prestamo(request):
    if not request.user.has_perm('gestion.ver_prestamos'):
        return HttpResponseForbidden()
    libros = Libro.objects.filter(disponible=True)
    usuarios = User.objects.all()
    if request.method == 'POST':
        libro_id = request.POST.get('libro')
        usuario_id = request.POST.get('usuario')
        fecha_prestamo = request.POST.get('fecha_prestamo')
        if libro_id and usuario_id and fecha_prestamo:
            libro = get_object_or_404(Libro, id=libro_id)
            usuario = get_object_or_404(User, id=usuario_id)
            prestamo = Prestamos.objects.create(libro=libro, 
                                                usuario=usuario, 
                                                fecha_prestamo=fecha_prestamo)
            libro.disponible = False
            libro.save()
            return redirect('lista_prestamos')
    fecha=(timezone.now().date()).isoformat()        
    return render(request, 'crear_prestamo.html', {'libros': libros,
                                                                    'usuarios': usuarios,
                                                                    'fecha': fecha})

def detalle_prestamo(request):
    pass

#--SECCION MULTAS--
def lista_multas(request):
    multas = Multa.objects.all()
    return render(request, 'multas.html', {'multas': multas})

def crear_multa(request):
    pass
def detalle_multa(request):
    pass
#--SECCION USUARIOS--
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'usuarios.html', {'usuarios': usuarios})

def crear_usuario(request):
    pass
def detalle_usuario(request):
    pass

#--SECCION REGISTRO--
def registro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
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
        form = UserCreationForm()
    return render(request, 'registration/registro.html', {'form': form})

#create your views here
from django.views.generic import ListView , CreateView , UpdateView , DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin,  PermissionRequiredMixin
from django.urls import reverse_lazy

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
    fields = ['titulo', 'autor', 'disponible']
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
