"""
Migración de datos: crea los tres roles del sistema como grupos de Django.
Al ser una migración, los roles existen en cualquier instalación nueva
(y también en la base de datos de pruebas).
"""
from django.db import migrations

ROLES = ("Administrador", "Operador", "Consulta")


def crear_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in ROLES:
        Group.objects.get_or_create(name=nombre)


def eliminar_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=ROLES).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(crear_roles, eliminar_roles),
    ]
