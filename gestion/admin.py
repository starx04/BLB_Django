from django.contrib import admin
from .models import Libro, Prestamos, Multa, Autor 
# Register your models here.
admin.site.register(Libro)
admin.site.register(Prestamos)
admin.site.register(Multa)
admin.site.register(Autor)