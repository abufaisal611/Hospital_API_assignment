from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone

# =====================================================================
# CUSTOM USER MANAGER & MODEL
# =====================================================================

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('Doctor', 'Doctor'),
        ('Patient', 'Patient'),
    )
    username = None  # Explicitly disabled as per your architecture
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)
    address = models.TextField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number']  # Fixed: Removed 'email' from here

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# =====================================================================
# DOCTOR MODEL
# =====================================================================

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    department = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    visiting_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        # Assignment Rule: Visiting fee cannot be negative
        if self.visiting_fee < 0:
            raise ValidationError("Visiting fee cannot be negative.")

    def __str__(self):
        return self.user.full_name


# =====================================================================
# APPOINTMENT MODEL
# =====================================================================

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments_as_patient')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments_as_doctor')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')

    class Meta:
        unique_together = ('doctor', 'appointment_date', 'appointment_time')

    def clean(self):
        # Assignment Rule: Appointment date cannot be in the past
        if self.appointment_date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past.")

    def __str__(self):
        # Fixed attributes to match model fields cleanly
        return f"Patient: {self.patient.full_name} - Doctor: {self.doctor.user.full_name} ({self.appointment_date})"


# =====================================================================
# BILL MODEL
# =====================================================================

class Bill(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        # Assignment Rule: Discount cannot be greater than consultation fee
        if self.discount > self.consultation_fee:
            raise ValidationError("Discount cannot be greater than consultation fee.")

    def save(self, *args, **kwargs):
        self.total_amount = self.consultation_fee - self.discount
        super().save(*args, **kwargs)