from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .permisos import ROLES, obtener_rol

Usuario = get_user_model()


# Qué hace: Se reciben y se validan los datos del login (usuario y contraseña).
# Qué usa: serializers.Serializer de DRF, un CharField para el usuario y otro para la contraseña.
# Cómo lo hace: La contraseña se marca como write_only para que nunca se devuelva en la respuesta.
#     La validación de verdad se hace en el método validate de abajo.
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    # Qué hace: Se revisa que el usuario y la contraseña sean correctos y que el usuario tenga un
    #     rol.
    # Qué usa: authenticate() de Django y la función obtener_rol.
    # Cómo lo hace: Se llama a authenticate con el usuario y la contraseña; si devuelve None se
    #     lanza el error "Usuario o contraseña incorrectos." (400). Si el usuario no tiene rol
    #     también se rechaza. Si todo está bien, se guarda el usuario en attrs para que la vista
    #     cree el token.
    def validate(self, attrs):
        usuario = authenticate(username=attrs["username"], password=attrs["password"])
        if usuario is None:
            raise serializers.ValidationError("Usuario o contraseña incorrectos.")
        if obtener_rol(usuario) is None:
            raise serializers.ValidationError("El usuario no tiene un rol asignado.")
        attrs["usuario"] = usuario
        return attrs


# Qué hace: Se convierte un usuario a JSON y se validan los datos para crear o editar usuarios.
# Qué usa: ModelSerializer de DRF, el modelo de usuario de Django, la lista ROLES y obtener_rol.
# Cómo lo hace: El campo rol es un ChoiceField que solo acepta los 3 roles y es write_only. La
#     contraseña también es write_only y no es obligatoria al editar.
class UsuarioSerializer(serializers.ModelSerializer):
    rol = serializers.ChoiceField(choices=ROLES, write_only=True)
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    # Qué hace: Se indica a qué modelo pertenece el serializador y qué campos se usan.
    # Qué usa: El modelo de usuario (Usuario) y la lista fields.
    # Cómo lo hace: Se ponen los campos que se reciben y se devuelven: id, username, nombre,
    #     apellido, correo, rol, password e is_active.
    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "email", "rol", "password", "is_active"]

    # Qué hace: Se agrega el rol del usuario a la respuesta en JSON.
    # Qué usa: to_representation de DRF y la función obtener_rol.
    # Cómo lo hace: Primero se arma el JSON normal con super() y luego se le agrega la llave "rol"
    #     con el nombre del grupo del usuario.
    def to_representation(self, instance):
        datos = super().to_representation(instance)
        datos["rol"] = obtener_rol(instance)
        return datos

    # Qué hace: Se valida la contraseña cuando se crea o se cambia un usuario.
    # Qué usa: validate_password de Django, que usa los AUTH_PASSWORD_VALIDATORS de settings.py.
    # Cómo lo hace: Si se está creando un usuario (no hay instance) y no viene contraseña, se da
    #     error 400. Si viene una contraseña, se revisa que cumpla los validadores (largo mínimo,
    #     que no sea común, etc.).
    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
        if attrs.get("password"):
            validate_password(attrs["password"])
        return attrs

    # Qué hace: Se crea un usuario nuevo con su contraseña y su rol.
    # Qué usa: transaction.atomic, set_password y Group.objects.get_or_create.
    # Cómo lo hace: Se sacan el rol y la contraseña de los datos, se crea el usuario y la
    #     contraseña se guarda cifrada con set_password. Después se busca o se crea el grupo del
    #     rol y se le asigna. Todo va dentro de una transacción para que se guarde todo junto o
    #     nada.
    @transaction.atomic
    def create(self, validated_data):
        rol = validated_data.pop("rol")
        password = validated_data.pop("password")
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        grupo, _ = Group.objects.get_or_create(name=rol)
        usuario.groups.set([grupo])
        return usuario

    # Qué hace: Se editan los datos de un usuario que ya existe, y si viene, también su contraseña
    #     y su rol.
    # Qué usa: transaction.atomic, setattr, set_password y Group.objects.get_or_create.
    # Cómo lo hace: Se sacan el rol y la contraseña, y los demás campos se copian al usuario con
    #     setattr. Si viene contraseña se cifra con set_password. Se guarda y, si viene rol, se
    #     cambia el grupo del usuario. Todo va dentro de una transacción.
    @transaction.atomic
    def update(self, instance, validated_data):
        rol = validated_data.pop("rol", None)
        password = validated_data.pop("password", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        if rol:
            grupo, _ = Group.objects.get_or_create(name=rol)
            instance.groups.set([grupo])
        return instance
