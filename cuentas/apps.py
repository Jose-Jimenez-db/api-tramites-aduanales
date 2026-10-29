from django.apps import AppConfig


# Qué hace: Se registra la app cuentas dentro del proyecto para que Django la reconozca.
# Qué usa: AppConfig de Django.
# Cómo lo hace: Se indica el nombre de la carpeta (name), el tipo de id automático (BigAutoField) y
#     el nombre que se ve en el panel /admin/ (verbose_name). Esta clase la crea startapp.
class CuentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cuentas"
    verbose_name = "Cuentas y roles"
