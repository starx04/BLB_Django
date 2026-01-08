from django.core.management.base import BaseCommand
from django.conf import settings
from decimal import Decimal
from gestion.models import Multa

class Command(BaseCommand):
    help = "Corrige multas con monto 0 aplicando el valor por defecto según su tipo"

    def handle(self, *args, **options):
        candidates = Multa.objects.filter(monto__lte=0)
        total = candidates.count()
        fixed = 0
        for m in candidates:
            old = m.monto
            if m.tipo == 'r':
                monto = Decimal(m.prestamo.multa_retraso)
            elif m.tipo == 'd':
                monto = Decimal(getattr(settings, 'MULTA_DETERIORO', 10))
            elif m.tipo == 'p':
                monto = Decimal(getattr(settings, 'MULTA_PERDIDA', 50))
            else:
                monto = None

            if monto and monto != old:
                m.monto = monto
                m.save()
                fixed += 1
                self.stdout.write(self.style.SUCCESS(f'Actualizada multa {m.codigo}: {old} -> {m.monto}'))
        self.stdout.write(self.style.NOTICE(f'Total revisadas: {total}, actualizadas: {fixed}'))
