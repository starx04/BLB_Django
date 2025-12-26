from django import forms

class BusquedaLibroForm(forms.Form):
    termino = forms.CharField(
        label="Buscar por Título o Autor",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Harry Potter'})
    )
    isbn = forms.CharField(
        label="Buscar por ISBN",
        max_length=13,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 9780123456789'})
    )

    def clean(self):
        datos = super().clean()
        termino = datos.get("termino")
        isbn = datos.get("isbn")

        if not termino and not isbn:
            raise forms.ValidationError("Ingresa un término o un ISBN.")
        
        return datos
