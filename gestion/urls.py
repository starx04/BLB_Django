from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", index, name="index"),

    # Gestion Usuarios y Auth
    path('usuarios/', lista_usuarios, name="lista_usuarios"),
    path('usuarios/<int:id>/', detalle_usuario, name="detalle_usuario"),
    path('login/', auth_views.LoginView.as_view(), name="login"),
    path('logout/', auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name="password_change"),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path('registro/', registro, name="registro"),

    # Libros
    path('libros/', lista_libros, name="lista_libros"),
    path('libros/nuevo/', crear_libros, name="crear_libros"),
    
    # Autores
    path('autores/', lista_autores, name="lista_autores"),
    path('autores/nuevo/', crear_autor, name="crear_autor"),
    path('autores/<int:id>/editar/', crear_autor, name="editar_autor"),
    
    # Préstamos
    path('prestamos/', lista_prestamos, name="lista_prestamos"),
    path('prestamos/nuevo/', crear_prestamo, name="crear_prestamo"),
    path('prestamos/<int:id>/finalizar/', finalizar_prestamo, name="finalizar_prestamo"),
    path('prestamos/<int:id>/renovar/', renovar_prestamo, name="renovar_prestamo"),
    path('prestamos/<int:id>/aceptar/', aceptar_solicitud, name="aceptar_solicitud"),
    path('prestamos/<int:id>/rechazar/', rechazar_solicitud, name="rechazar_solicitud"),
    
    # Multas
    path('multas/', lista_multas, name="lista_multa"),
    path('multas/<int:id>/pagar/', pagar_multa, name="pagar_multa"),

    # Admin Panel
    path('admin_panel/', panel_administracion, name="panel_administracion"),
    path('admin_panel/empleado/nuevo/', crear_empleado, name="crear_empleado"),

    # Reportes PDF
    path('reportes/auditoria/', generar_reporte_auditoria_pdf, name="reporte_auditoria_pdf"),
    path('reportes/multas/', generar_reporte_multas_pdf, name="reporte_multas_pdf"),

    # API
    path('api/buscar/', buscar_libro_api, name="buscar_libro_api"),
    path('api/guardar/', guardar_libro_api, name="guardar_libro_api"),
]