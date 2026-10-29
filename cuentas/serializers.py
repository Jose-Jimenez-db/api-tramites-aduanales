from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .permisos import ROLES, obtener_rol

Usuario = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        usuario = authenticate(username=attrs["username"], password=attrs["password"])
        if usuario is None:
            raise serializers.ValidationError("Usuario o contraseña incorrectos.")
        if obtener_rol(usuario) is None:
            raise serializers.ValidationError("El usuario no tiene un rol asignado.")
        attrs["usuario"] = usuario
        return attrs


class UsuarioSerializer(serializers.ModelSerializer):
    rol = serializers.ChoiceField(choices=ROLES, write_only=True)
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    class Meta:
        model = Usuario
        fields = ["id", "username", "first_name", "last_name", "email", "rol", "password", "is_active"]

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        datos["rol"] = obtener_rol(instance)
        return datos

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
        if attrs.get("password"):
            validate_password(attrs["password"])
        return attrs

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
