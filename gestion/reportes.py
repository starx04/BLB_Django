from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from django.http import HttpResponse
from django.utils import timezone
from gestion.models import RegistroAuditoria, Prestamos, Multa
from django.contrib.auth.decorators import login_required

@login_required
def generar_reporte_auditoria_pdf(request):
    """
    Genera un PDF con el registro de todas las acciones del sistema.
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_auditoria_{timezone.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
    # Crear el PDF
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    title = Paragraph("REPORTE DE AUDITORÍA - BIBLIOTECA", title_style)
    elements.append(title)
    
    subtitle = Paragraph(f"Generado el: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    elements.append(subtitle)
    elements.append(Spacer(1, 0.3*inch))
    
    # Obtener registros (últimos 50)
    registros = RegistroAuditoria.objects.all()[:50]
    
    # Crear tabla
    data = [['Fecha/Hora', 'Usuario', 'Acción', 'Descripción']]
    
    for reg in registros:
        data.append([
            reg.fecha_hora.strftime('%d/%m/%Y %H:%M'),
            str(reg.usuario.username if reg.usuario else 'Sistema'),
            reg.get_accion_display(),
            reg.descripcion[:60] + '...' if len(reg.descripcion) > 60 else reg.descripcion
        ])
    
    table = Table(data, colWidths=[1.5*inch, 1.2*inch, 1.5*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    return response

@login_required
def generar_reporte_multas_pdf(request):
    """
    Genera un PDF con el estado de todas las multas (pagadas y pendientes).
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_multas_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    title = Paragraph("REPORTE DE MULTAS - BIBLIOTECA", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Estadísticas
    multas_pendientes = Multa.objects.filter(pagada=False)
    multas_pagadas = Multa.objects.filter(pagada=True)
    total_pendiente = sum([m.monto for m in multas_pendientes])
    total_recaudado = sum([m.monto for m in multas_pagadas])
    
    stats_text = f"""
    <b>Total Multas Pendientes:</b> {multas_pendientes.count()} (${total_pendiente:.2f})<br/>
    <b>Total Multas Pagadas:</b> {multas_pagadas.count()} (${total_recaudado:.2f})
    """
    elements.append(Paragraph(stats_text, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Tabla de multas pendientes
    elements.append(Paragraph("<b>MULTAS PENDIENTES</b>", styles['Heading2']))
    
    data = [['Código', 'Usuario', 'Tipo', 'Monto', 'Fecha']]
    for multa in multas_pendientes:
        data.append([
            multa.codigo,
            multa.prestamo.usuario.username,
            multa.get_tipo_display(),
            f"${multa.monto}",
            multa.fecha.strftime('%d/%m/%Y')
        ])
    
    if len(data) > 1:
        table = Table(data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e74c3c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No hay multas pendientes.", styles['Normal']))
    
    doc.build(elements)
    return response
