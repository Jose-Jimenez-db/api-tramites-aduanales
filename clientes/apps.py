from django.apps import AppConfig


# Qué hace: Se registra la app clientes dentro del proyecto.
# Qué usa: AppConfig de Django.
# Cómo lo hace: Se indica el nombre de la carpeta, el tipo de id automático (BigAutoField) y el
#     nombre que se ve en el admin. Esta clase la crea startapp.
class ClientesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clientes"
    verbose_name = "Clientes"
