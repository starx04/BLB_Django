from django import forms
from django.contrib.auth.forms import UserCreationForm as FormularioCreacionUsuario
from django.contrib.auth.models import User as Usuario
from .models import PerfilUsuario
from django.core.exceptions import ValidationError as ErrorValidacion

class FormularioBusquedaLibro(forms.Form):
    termino_busqueda = forms.CharField(
        label="Buscar por Título o Autor",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Harry Potter'})
    )
    codigo_isbn = forms.CharField(
        label="Buscar por ISBN",
        max_length=13,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 9780123456789'})
    )

    def clean(self):
        datos_limpios = super().clean()
        termino = datos_limpios.get("termino_busqueda")
        isbn = datos_limpios.get("codigo_isbn")

        if termino:
            datos_limpios['termino_busqueda'] = termino.strip()
        if isbn:
             datos_limpios['codigo_isbn'] = isbn.strip()

        if not datos_limpios.get('termino_busqueda') and not datos_limpios.get('codigo_isbn'):
            raise forms.ValidationError("Ingresa un término o un ISBN.")
        
        return datos_limpios

class FormularioRegistroExtendido(FormularioCreacionUsuario):
    dni = forms.CharField(max_length=20, required=True, label="DNI / Identificación")
    direccion = forms.CharField(max_length=200, required=False, label="Dirección")
    telefono = forms.CharField(max_length=20, required=False, label="Teléfono")

    class Meta(FormularioCreacionUsuario.Meta):
        model = Usuario
        fields = FormularioCreacionUsuario.Meta.fields + ('email',)
        
    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if not dni.isdigit():
             raise ErrorValidacion("El DNI debe contener solo números.")
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not telefono.isdigit():
             raise ErrorValidacion("El teléfono debe contener solo números.")
        return telefono

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if commit:
            usuario.save()
            # El perfil se crea por la señal post_save, ahora lo actualizamos
            if hasattr(usuario, 'perfil'):
                perfil_usuario = usuario.perfil
                perfil_usuario.dni = self.cleaned_data['dni']
                perfil_usuario.direccion = self.cleaned_data['direccion']
                perfil_usuario.telefono = self.cleaned_data['telefono']
                perfil_usuario.save()
        return usuario
