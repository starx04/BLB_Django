from django.urls import path
from .view import *

urlpatterns = [
    path("",index,name="index"),
    #Libros
    path('libros/',lista_libros,name="lista_libros"),
    path('libros/nuevo/',crear_libro,name="crear_libro"),
    #Autores
    path('autores/',lista_autores,name="lista_autores"),
    path('autores/nuevo',crear_autor,name="crear_autor"),
    #Prestamos
    path('prestamos/',lista_prestamos,name="lista_prestamos"),
    path('prestamos/nuevo',crear_prestamo,name="crear_prestamo")
]