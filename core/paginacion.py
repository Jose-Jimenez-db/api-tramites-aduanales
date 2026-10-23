from rest_framework.pagination import PageNumberPagination


class PaginacionEstandar(PageNumberPagination):
    """
    Paginación por número de página.

    ?pagina=2        -> número de página
    ?tamano=20       -> cantidad de registros por página (máximo 100)
    """

    page_size = 10
    page_query_param = "pagina"
    page_size_query_param = "tamano"
    max_page_size = 100
