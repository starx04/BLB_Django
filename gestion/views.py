from django.shortcuts import render,redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings 

from .models import Libro, Prestamos, Multa, Autor

def index(request):
    titulo2 = "Hola Mundo"
    title = settings.TITLE
    return render(request, 'gestion/templates/home.html', {'titulo': title, "t": titulo2})
#-- SECCION LIBROS --
def lista_libros(request):
    libros = Libro.objects.all()
    return render(request, 'gestion/templates/libros.html', {'libros': libros})

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
    return render(request, 'gestion/templates/crear_libros.html')
#-- SECCION AUTORES --
def editar_autor(request):
    autor = get_object_or_404(Autor, id=request.POST.get('id'))
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        if nombre and apellido:
            autor.nombre = nombre
            autor.apellido = apellido
            autor.bibliografia = bibliografia
            autor.save()
            return redirect('lista_autores')
    return render(request, 'gestion/templates/editar_autor.html', {'autor': autor})

def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'gestion/templates/autores.html', {'autores': autores})

def crear_autor(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        bibliografia = request.POST.get('bibliografia')
        Autor.objects.create(nombre=nombre, apellido=apellido, bibliografia=bibliografia)
        return redirect('lista_autores')
    return render(request, 'gestion/templates/crear_autor.html')
#--SECCION PRESTAMOS--
def lista_prestamos(request):
    prestamos = Prestamos.objects.all()
    return render(request, 'gestion/templates/prestamos.html', {'prestamos': prestamos})

def crear_prestamo(request):
    pass

def detalle_prestamo(request):
    pass

#--SECCION MULTAS--
def lista_multas(request):
    multas = Multa.objects.all()
    return render(request, 'gestion/templates/multas.html', {'multas': multas})

def crear_multa(request):
    pass
def detalle_multa(request):
    pass
#--SECCION USUARIOS--
def lista_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'gestion/templates/usuarios.html', {'usuarios': usuarios})
def crear_usuario(request):
    pass
def detalle_usuario(request):
    pass
