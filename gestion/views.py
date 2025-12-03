from django.shortcuts import render,redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings 

from .models import Author, Libro, Prestamos, Multa

def index(request):
    titulo2 = "Hola Mundo"
    title = settings.TITLE
    return render(request, 'gestion/templates/home.html', {'titulo': title, "t": titulo2})

def lista_libros(request):
    pass

def lista_autores(request):
    autores = Autor.objects.all()
    return render(request, 'gestion/templates/autores.html', {'autores': autores})

def lista_prestamos(request):
    pass

def lista_multas(request):
    pass

def crear_prestamo(request):
    pass

def detalle_prestamo(request):
    pass
