from django.db import models
from django.conf import settings #Libreria que se usa pra usar los usraios de  django
from django.utils import timezone

# Create your models here.

class Author(models.Model):
    nombre=models.CharField(max_length=50)
    apellido=models.CharField(max_length=50)
    bibliografia  = models.CharField(max_length=200, blank= True, null= True)
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} {self.bibliografia}"
    
class Libro(models.Model):
    titulo=models.CharField(max_length=50)
    author=models.ForeignKey(Author,related_name="Libro", on_delete= models.PROTECT)
    disponible = models.BooleanField(default=True)
    bibliografia  = models.CharField(max_length=200, blank= True, null= True)
    
    def __str__(self):
        return self.titulo
    
class Prestamos(models.Model):
    libro= models.ForeignKey(Libro, related_name="Prestamos", on_delete= models.PROTECT)
    usuario =models.ForeignKey(settings.AUTH_USER_MODEL, related_name="Prestamos" , on_delete= models.PROTECT)
    fecha =models.DateField(default=timezone.now)
    fecha_max=models.DateField()
    fecha_devolucion = models.DateField(blank=True, null=True) #Permite a django grabar en blanco y en nulo
    
    def __str__(self):
        return f"Prestamo de {self.libro} a {self.usuario}"
    
    @property #Sirve similiar al compute de odoo
    def dias_retraso(self):
        hoy = timezone.now().date()
        fecha_ref =  self.fecha_devolucion or hoy
        if  fecha_ref > self.fecha_max:
            return (fecha_ref + self.fecha_devolucion).days
    @property
    def multa_retraso(self):
        tarifa = 0.50
        return self.dias_retraso * tarifa
    
class Multa(models.Model):
    prestamo =  models.ForeignKey(Prestamos, related_name="Multa", on_delete= models.PROTECT)
    tipo = models.CharField(max_length=10, choices=(('r','retraso'), ('p','perdida'), ('d', 'deterioro')))
    monto = models.DecimalField(max_length=3, decimal_places=2, default=0, max_digits=4)
    pagada  = models.BooleanField(default=False)
    fecha  =  models.DateField(default=timezone.now)
        
        
    def __str__(self):
        return f"Multa {self.tipo} - {self.monto} - {self.prestamo}"
        
    def save(self, *args, **kwargs):
        if self.tipo ==  'r' and  self.monto ==0 :
            self.monto = self.prestamo.multa_retraso
        super().save(*args ,**kwargs) #Llama a la funcion principal de djnago 