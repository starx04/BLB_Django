from django.db import models
from django.conf import settings #Libreria que se usa pra usar los usraios de  django
from django.utils import timezone

# Create your models here.

class Autor(models.Model):
    nombre=models.CharField(max_length=50)
    apellido=models.CharField(max_length=50)
    bibliografia  = models.CharField(max_length=200, blank= True, null= True)
    imagen = models.ImageField(upload_to='autores/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} {self.bibliografia}"
    
class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.nombre

class Libro(models.Model):
    titulo=models.CharField(max_length=50)
    autor=models.ForeignKey(Autor,related_name="Libro", on_delete= models.PROTECT)
    categorias = models.ManyToManyField(Categoria, blank=True)
    # Stock total de copias físicas
    stock = models.PositiveIntegerField(default=1) 
    bibliografia  = models.CharField(max_length=200, blank= True, null= True)
    isbn = models.CharField(max_length=13, blank=True, null=True, unique=True)
    imagen = models.ImageField(upload_to='libros/', blank=True, null=True)

    def __str__(self):
        return self.titulo
    
    @property
    def disponibles(self):
        # Calcula cuantos libros quedan en estanteria
        # (Stock Total) - (Libros actualmente prestados y no devueltos)
        prestados = self.Prestamos.filter(fecha_devolucion__isnull=True).count()
        return self.stock - prestados

    @property
    def esta_disponible(self):
        return self.disponibles > 0
    
import uuid

def generar_codigo_unico(prefix):
    """Genera un código único corto con un prefijo dado."""
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"

class Prestamos(models.Model):
    codigo = models.CharField(max_length=20, unique=True, editable=False, null=True) # null=True temporalmente para evitar error en migracion directa
    libro = models.ForeignKey(Libro, related_name="Prestamos", on_delete= models.PROTECT)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="Prestamos" , on_delete= models.PROTECT)
    fecha = models.DateField(default=timezone.now)
    fecha_max = models.DateField()
    fecha_devolucion = models.DateField(blank=True, null=True) #Permite a django grabar en blanco y en nulo
    
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('prestado', 'Prestado'),
        ('devuelto', 'Devuelto'),
        ('multado', 'Multado')
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    renovaciones = models.PositiveIntegerField(default=0)
    
    class Meta:
        permissions = (
            ("ver_prestamos", "Puede Ver Prestamos"),
            ("gestionar_prestamos", "Puede Gestionar Prestamos"),
        )


    def __str__(self):
        return f"Prestamo {self.codigo} ({self.estado}) - {self.libro} a {self.usuario}"
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo_unico("PRES")
        super().save(*args, **kwargs)

    def confirmar(self):
        """Confirma un borrador y activa el préstamo."""
        if self.estado == 'borrador':
            self.estado = 'prestado'
            self.fecha = timezone.now().date()
            # Plazo fijo de 7 días (1 semana) desde la fecha de préstamo
            if not self.fecha_max:
                self.fecha_max = self.fecha + timezone.timedelta(days=7)
            self.save()

    def finalizar(self):
        if not self.fecha_devolucion:
            self.fecha_devolucion = timezone.now().date()
            self.estado = 'devuelto'
            self.save()
            
            # Generar multa automática si hubo retraso
            if self.dias_retraso > 0:
                self.Multa.create(tipo='r')

    def renovar(self, dias=7):
        if self.estado == 'prestado' and self.renovaciones < 3:
            self.fecha_max += timezone.timedelta(days=dias)
            self.renovaciones += 1
            self.save()
            return True
        return False

    def comprobar_vencimiento(self):
        """Verifica si el préstamo ha vencido y actualiza el estado."""
        if self.estado == 'prestado' and self.fecha_max < timezone.now().date():
            self.estado = 'multado'
            self.save()
            return True
        return False

    @property #Sirve similiar al compute de odoo
    def dias_retraso(self):
        if self.estado == 'devuelto':
            fecha_ref = self.fecha_devolucion
        else:
            fecha_ref = timezone.now().date()
            
        if fecha_ref > self.fecha_max:
             return (fecha_ref - self.fecha_max).days
        return 0
    @property
    def multa_retraso(self):
        tarifa = 0.50
        return self.dias_retraso * tarifa
    
class Multa(models.Model):
    codigo = models.CharField(max_length=20, unique=True, editable=False, null=True)
    prestamo =  models.ForeignKey(Prestamos, related_name="Multa", on_delete= models.PROTECT)
    tipo = models.CharField(max_length=10, choices=(('r','retraso'), ('p','perdida'), ('d', 'deterioro')))
    monto = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pagada  = models.BooleanField(default=False)
    fecha  =  models.DateField(default=timezone.now)
        
    def __str__(self):
        return f"Multa {self.codigo} ({self.tipo}) - {self.monto}"
        
    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo_unico("MULT")
        if self.tipo ==  'r' and  self.monto ==0 :
            self.monto = self.prestamo.multa_retraso
        super().save(*args, **kwargs) 

# Extension del Usuario Django
from django.db.models.signals import post_save
from django.dispatch import receiver

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil')
    codigo_socio = models.CharField(max_length=20, unique=True, editable=False, null=True)
    dni = models.CharField(max_length=20, blank=True, null=True, unique=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.codigo_socio:
            self.codigo_socio = generar_codigo_unico("SOC")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Perfil {self.codigo_socio} - {self.usuario.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(usuario=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def guardar_perfil_usuario(sender, instance, **kwargs):
    try:
        instance.perfil.save()
    except PerfilUsuario.DoesNotExist:
        # En caso de usuarios antiguos sin perfil
        PerfilUsuario.objects.create(usuario=instance) 

class Gasto(models.Model):
    concepto = models.CharField(max_length=100)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(default=timezone.now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.concepto} - ${self.monto}" 