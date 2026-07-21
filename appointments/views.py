from rest_framework import viewsets, filters, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .models import Doctor, Appointment, Bill
from .serializers import (
    DoctorSerializer, 
    AppointmentSerializer, 
    UserSerializer, 
    BillSerializer, 
    RegistrationSerializer,
    MyTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer 
)
from .permissions import IsAdminUserRole, AppointmentPermission

User = get_user_model()

# =====================================================================
# REGISTRATION & USER MANAGEMENT (Patient Signup / Admin Control)
# =====================================================================
class RegistrationViewSet(viewsets.ModelViewSet):
    """
    Handles Patient registration (anyone can POST).
    Also allows Admins to view users or change a patient's role to 'Doctor'.
    """
    queryset = User.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RegistrationSerializer  # Anyone can register using this schema
        return UserSerializer  # Admin sees normal user details

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [IsAdminUserRole()]  # Only Admin can update/list users (e.g., upgrade to Doctor)
    

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response({"message": "Password reset link sent to email."}, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response({"message": "Password has been successfully updated."}, status=status.HTTP_200_OK)


# =====================================================================
# LOGIN VIEW (JWT Token Authentication)
# =====================================================================
class LoginView(TokenObtainPairView):
    
    serializer_class = MyTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


# =====================================================================
# DOCTOR VIEWSET (Watching Doctors - Open to Public)
# =====================================================================
class DoctorViewSet(viewsets.ModelViewSet):
    
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer  
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Requirements mapping
    filterset_fields = ['department']
    search_fields = ['user__full_name', 'specialization']  
    ordering_fields = ['visiting_fee']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUserRole()]
        return [permissions.AllowAny()]


# =====================================================================
# APPOINTMENT VIEWSET (Role-Based Appointment Control)
# =====================================================================
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Handles appointment creation. Filters rows automatically based on the logged-in user:
    - Admin: Sees all records.
    - Doctor: Sees only appointments assigned to them.
    - Patient: Sees only their own booked appointments.
    """
    serializer_class = AppointmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = ['status', 'doctor']
    search_fields = ['patient__full_name', 'doctor__user__full_name']  
    ordering_fields = ['appointment_date']
    permission_classes = [AppointmentPermission]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Appointment.objects.none()
            
        if user.role == 'Admin':
            return Appointment.objects.all()
        elif user.role == 'Doctor':
            # Safely filters using the doctor profile relation mapping
            return Appointment.objects.filter(doctor__user=user)
        return Appointment.objects.filter(patient=user)

    def perform_create(self, serializer):
        # Force the patient to be the logged-in user if a patient is making the booking
        if self.request.user.role == 'Patient':
            serializer.save(patient=self.request.user)
        else:
            serializer.save()  # Admin can specify any target patient ID manually


# =====================================================================
# BILLING VIEWSET (Only Admin Access for Confirmed Appointments)
# =====================================================================
class BillViewSet(viewsets.ModelViewSet):
    """
    Allows management of bills. Validates requests to ensure bills are 
    only generated for confirmed appointments.
    """
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    permission_classes = [IsAdminUserRole]  # Secured for Admin usage only

    def create(self, request, *args, **kwargs):
        appointment_id = request.data.get('appointment')
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            # Enforce confirmation validation constraints
            if appointment.status != 'Confirmed':
                return Response(
                    {"error": "Cannot generate a bill for an appointment that is not confirmed."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Appointment.DoesNotExist:
            return Response({"error": "Target appointment does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        return super().create(request, *args, **kwargs)


# =====================================================================
# DASHBOARD SUMMARY VIEW
# =====================================================================
class DashboardSummaryView(APIView):
    """
    Provides a simple summary overview context for dashboard display metrics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "total_patients": User.objects.filter(role='Patient').count(),
            "total_doctors": Doctor.objects.count(),
            "total_appointments": Appointment.objects.count(),
            "pending_appointments": Appointment.objects.filter(status='Pending').count(),
            "confirmed_appointments": Appointment.objects.filter(status='Confirmed').count(),
            "completed_appointments": Appointment.objects.filter(status='Completed').count(),
        }, status=status.HTTP_200_OK)
