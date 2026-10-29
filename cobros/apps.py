from django.apps import AppConfig


# Qué hace: Se registra la app cobros dentro del proyecto.
# Qué usa: AppConfig de Django.
# Cómo lo hace: Se indica el nombre de la carpeta, el tipo de id automático y el nombre del admin.
#     La crea startapp.
class CobrosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cobros"
    verbose_name = "Cobros"
