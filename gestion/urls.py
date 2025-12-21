from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("",index,name="index"),

    #Path class views
    path('libros_list/', LibroListView.as_view(), name="libro_list"),
    path('libros/nuevo/', LibroCreateView.as_view(), name="libro_create"),
    path('libros/<int:pk>/editar/', LibroUpdateView.as_view(), name="libro_update"),
    path('libros/<int:pk>/eliminar/', LibroDeleteView.as_view(), name="libro_delete"),
    path('libros/<int:pk>/', LibroDetailView.as_view(), name="libro_detail"),

    #Gestion Usuarios
    path('login/',auth_views.LoginView.as_view(),name="login"),
    path('logout/',auth_views.LogoutView.as_view(next_page="login"),name="logout"),

    #Cambio de contraseña
    path('password_change/',auth_views.PasswordChangeView.as_view(),name="password_change"),
    path('password_change/done/',auth_views.PasswordChangeDoneView.as_view(),name="password_change_done"),
    
    #Registro
    path('registro/',registro,name="registro"),

    #Libros
    path('libros/',lista_libros,name="lista_libros"),
    path('libros/nuevo/',crear_libros,name="crear_libros"),
    
    #Autores
    path('autores/',lista_autores,name="lista_autores"),
    path('autores/nuevo',crear_autor,name="crear_autor"),
    path('autores/<int:id>/editar',crear_autor,name="editar_autor"),
    
    #Prestamos
    path('prestamos/', lista_prestamos, name="lista_prestamos"),
    path('prestamos/nuevo/', crear_prestamo, name="crear_prestamo"),
    path('prestamos/<int:id>', detalle_prestamo, name="detalle_prestamo"),
    
    #Multas
    path('multas/', lista_multas, name="lista_multa"),
    path('multas/nuevo/<int:prestamo_id>', crear_multa, name="crear_multa"),

    # API
    path('api/buscar/', buscar_libro_api, name="buscar_libro_api"),
]