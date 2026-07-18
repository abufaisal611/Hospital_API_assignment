from rest_framework import permissions

class IsAdminUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'Admin'

class IsDoctorUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == 'Doctor'

class AppointmentPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        role = request.user.profile.role
        if role == 'Admin':
            return True
        elif role == 'Doctor':
            return obj.doctor.id == request.user.id  # Assuming mapping or matching structure
        elif role == 'Patient':
            return obj.patient == request.user
        else:
            return False