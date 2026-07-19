from rest_framework import serializers
from .models import Doctor, Appointment, User, Bill
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone

User = get_user_model()

# =====================================================================
# USER & PROFILE SERIALIZERS
# =====================================================================

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', "full_name", "phone_number", "address" ] 
        read_only_fields = ['id', 'email', 'role'] 

# =====================================================================
# DOCTOR MANAGEMENT SERIALIZER
# =====================================================================

class DoctorSerializer(serializers.ModelSerializer):
    # Pulls full name directly from the linked Custom User object dynamically
    name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'user', 'name', 'department', 'specialization', 'visiting_fee']
        extra_kwargs = {
            'user': {'write_only': True}  # Use user ID when creating a doctor profile 
        }

    def validate_visiting_fee(self, value):
        # Assignment Rule: Visiting fee cannot be negative 
        if value < 0:
            raise serializers.ValidationError("Visiting fee cannot be negative.")
        return value


# =====================================================================
# APPOINTMENT MANAGEMENT SERIALIZER
# =====================================================================

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_name', 'doctor', 'doctor_name', 'appointment_date', 'appointment_time', 'status']
        read_only_fields = ['id']
        # Fixed: Correct style for date and time fields in DRF
        extra_kwargs = {
            'appointment_date': {'style': {'input_type': 'date'}},
            'appointment_time': {'style': {'input_type': 'time'}},
        }

    def validate_appointment_date(self, value):
        # Assignment Rule: Appointment date cannot be in the past 
        if value < timezone.now().date():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        return value


# =====================================================================
# BILLING SERIALIZER
# =====================================================================

class BillSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Bill
        fields = ['id', 'patient', 'doctor', 'appointment', 'consultation_fee', 'discount', 'total_amount']
        read_only_fields = ['id', 'total_amount']

    def validate(self, attrs):
        # Gracefully handle validation during partial update (PATCH) requests
        consultation_fee = attrs.get('consultation_fee', self.instance.consultation_fee if self.instance else 0)
        discount = attrs.get('discount', self.instance.discount if self.instance else 0)

        # Assignment Rule: Discount cannot be greater than consultation fee 
        if discount > consultation_fee:
            raise serializers.ValidationError({"discount": "Discount cannot be greater than consultation fee."})
        return attrs


# =====================================================================
# AUTHENTICATION & REGISTRATION SERIALIZERS
# =====================================================================

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['full_name'] = user.full_name
        token['role'] = user.role
        return token


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['email', 'full_name', 'phone_number', 'address', 'password', 'confirm_password']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Explicit validation fallback ensuring data clean criteria 
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email must be unique."})
        if User.objects.filter(phone_number=attrs['phone_number']).exists():
            raise serializers.ValidationError({"phone_number": "Phone number must be unique."})
            
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        # Safely extract email matching custom user manager parameters
        email = validated_data.pop('email')
        user = User.objects.create_user(email=email, **validated_data)
        return user