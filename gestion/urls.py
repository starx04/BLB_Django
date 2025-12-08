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
    path('autores/<int:id>/editar',editar_autor,name="editar_autor"),
    #Prestamos
    path('prestamos/', lista_prestamos, name="lista_prestamos"),
    path('prestamos/nuevo/', crear_prestamo, name="crear_prestamo"),
    path('prestamos/<int:id>', detalle_prestamo, name="detalle_prestamo"),
    #Multas
    path('multas/', lista_multas, name="lista_multa"),
    path('multas/nuevo/<int:prestamo_id>', crear_multa, name="crear_multa"),
]