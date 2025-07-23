from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.views import (
    SessionListView, SessionDestroyAPIView,
    LeaderBoardListAPIView, GetStudentHomeworkListAPIView,
     StudentSubmissionListAPIView,
    RegisterCreateAPIView, TeacherHomeworkViewSet,
    TeacherGroupViewSet, TeacherSubmissionViewSet,
    TeacherViewSet, StudentViewSet, GroupViewSet,
    StudentHomeworkViewSet, StudentSubmissionViewSet
)

urlpatterns = [
    # Auth
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/register/', RegisterCreateAPIView.as_view(), name='register'),
    path('api/auth/sessions/', SessionListView.as_view(), name='sessions_list'),
    path('api/auth/sessions/<int:pk>/', SessionDestroyAPIView.as_view(), name='session_delete'),

    # Student
    path('api/student/leaderboard/', LeaderBoardListAPIView.as_view(), name='student_leaderboard'),
    path('api/student/homework/', GetStudentHomeworkListAPIView.as_view(), name='student_homework_list'),
    path('api/student/submissions/', StudentSubmissionListAPIView.as_view(), name='student_submissions'),
]

# Teacher routes
teacher_router = DefaultRouter()
teacher_router.register(r'teacher/homework', TeacherHomeworkViewSet, basename='teacher-homework')
teacher_router.register(r'teacher/groups', TeacherGroupViewSet, basename='teacher-groups')
teacher_router.register(r'teacher/submissions', TeacherSubmissionViewSet, basename='teacher-submissions')

# Admin routes
admin_router = DefaultRouter()
admin_router.register(r'admin/teachers', TeacherViewSet, basename='admin-teachers')
admin_router.register(r'admin/students', StudentViewSet, basename='admin-students')
admin_router.register(r'admin/groups', GroupViewSet, basename='admin-groups')

# Student ViewSet routes
student_router = DefaultRouter()
student_router.register(r'student/homework', StudentHomeworkViewSet, basename='student-homework')
student_router.register(r'student/submissions', StudentSubmissionViewSet, basename='student-submissions')

urlpatterns += [
    path('api/', include(teacher_router.urls)),
    path('api/', include(admin_router.urls)),
    path('api/', include(student_router.urls)),
]
