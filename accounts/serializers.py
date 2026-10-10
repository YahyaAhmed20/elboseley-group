from rest_framework import serializers
from .models import مستخدم

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = مستخدم
        fields = ['id', 'username', 'password', 'اسم_كامل', 'نوع_الدور', 'is_active']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = مستخدم(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance