def roles(request):
    """Context processor que expone banderas de rol para todas las plantillas."""
    user = getattr(request, 'user', None)
    is_authenticated = user.is_authenticated if user else False

    is_admin = is_authenticated and (user.is_superuser or user.groups.filter(name='Administrador').exists())
    is_cliente = is_authenticated and user.groups.filter(name='Cliente').exists()
    is_bibliotecario = is_authenticated and user.groups.filter(name='Bibliotecario').exists()
    is_bodeguero = is_authenticated and user.groups.filter(name='Bodeguero').exists()

    can_add_books = is_authenticated and (user.is_superuser or user.groups.filter(name__in=['Bodeguero', 'Administrador']).exists())
    can_manage_authors = can_add_books

    can_view_prestamos = is_authenticated and (is_bibliotecario or is_cliente or is_admin)
    can_view_multas = is_authenticated and (is_bibliotecario or is_cliente or is_admin)

    return {
        'is_admin': is_admin,
        'is_cliente': is_cliente,
        'is_bibliotecario': is_bibliotecario,
        'is_bodeguero': is_bodeguero,
        'can_add_books': can_add_books,
        'can_manage_authors': can_manage_authors,
        'can_view_prestamos': can_view_prestamos,
        'can_view_multas': can_view_multas,
    }