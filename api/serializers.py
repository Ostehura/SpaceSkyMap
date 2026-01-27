from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("username", "password", "password2", "email")

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
    
    
    
    
class UserUpdateSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)

    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    new_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if not any(k in attrs for k in ("email", "username", "new_password")):
            raise serializers.ValidationError(
                "Fill at least one field to update (email, login or password)."
            )
        return attrs

    def validate_username(self, value: str) -> str:
        user = self.context["request"].user
        if User.objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value: str) -> str:
        user = self.context["request"].user
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("This email is already taken.")
        return value

    def update(self, instance, validated_data):
        validated_data.pop("old_password", None)

        if "email" in validated_data:
            instance.email = validated_data["email"]

        if "username" in validated_data:
            instance.username = validated_data["username"]

        if "new_password" in validated_data:
            instance.set_password(validated_data["new_password"])

        instance.save()
        return instance

