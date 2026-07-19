# appointments/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Doctor

@receiver(post_save, sender=User)
def manage_user_profiles(sender, instance, created, **kwargs):
    """
    Listens to the User model. If a new doctor user is created, 
    it automatically provisions their Doctor profile.
    """
    # Fixed: Checked for 'Doctor' (capitalized) to match your User choices
    if instance.role == 'Doctor':
        Doctor.objects.get_or_create(user=instance)

@receiver(post_save, sender=Doctor)
def sync_user_role_to_doctor(sender, instance, created, **kwargs):
    """
    Whenever a Doctor profile is created or updated, ensure the 
    linked user's role is automatically forced to 'Doctor'.
    """
    user = instance.user
    # Fixed: Checked for 'Doctor' (capitalized) to match your User choices
    if user.role == 'Patient':
        user.role = 'Doctor'
        user.save(update_fields=['role'])