from django.apps import AppConfig


# Qué hace: Se registra la app cargas dentro del proyecto.
# Qué usa: AppConfig de Django.
# Cómo lo hace: Se indica el nombre de la carpeta, el tipo de id automático y el nombre del admin.
#     La crea startapp.
class CargasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cargas"
    verbose_name = "Cargas"
