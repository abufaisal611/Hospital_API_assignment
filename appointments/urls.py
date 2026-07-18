from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegistrationViewSet, 
    CustomLoginView, 
    DoctorViewSet, 
    AppointmentViewSet, 
    BillViewSet, 
    DashboardSummaryView
)

router = DefaultRouter()
router.register(r'register', RegistrationViewSet, basename='user-registration')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'billing', BillViewSet, basename='billing')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', CustomLoginView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]