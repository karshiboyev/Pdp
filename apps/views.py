from django.db.models import Sum
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.generics import DestroyAPIView, CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action

from apps.models import UserSession, User, Homework, Group, Submission, Grade
from apps.permission import IsAdmin, IsTeacher, IsStudent
from apps.serializer import (
    CreateSubmissionSerializer, UserSerializer, UserProfileSerializer,
    TeacherSerializer, StudentSerializer, HomeworkSerializer,
    GroupSerializer, SubmissionSerializer, GradeSerializer
)


@extend_schema(tags=['auth'])
class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = UserSession.objects.filter(user=request.user)
        session_data = []

        for session in sessions:
            session_data.append({
                "jti": session.jti,
                "device": session.user_agent or "Unknown",
                "created": session.created_at,
            })

        return Response({"sessions": session_data})


@extend_schema(tags=['auth'])
class SessionDestroyAPIView(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = UserSession.objects.all()
    lookup_url_kwarg = 'pk'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


@extend_schema(tags=["auth"], responses=UserProfileSerializer)
class RegisterCreateAPIView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer


# STUDENT VIEWS
# _____________________________________________________________________________________________________
@extend_schema(tags=['student'])
class LeaderBoardListAPIView(ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        return (
            User.objects
            .filter(role='student')
            .annotate(total_score=Sum('submissions__final_grade'))
            .order_by('-total_score')[:10]
        )


@extend_schema(tags=['student'])
class GetStudentHomeworkListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = HomeworkSerializer

    def get_queryset(self):
        user = self.request.user

        if user.group:
            return Homework.objects.filter(group=user.group)
        return Homework.objects.none()


@extend_schema(tags=['student'])
class StudentSubmissionListAPIView(ListAPIView):
    serializer_class = CreateSubmissionSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        user = self.request.user
        return Submission.objects.filter(student=user)


# ADMIN/TEACHER MANAGEMENT VIEWS
# __________________________________________________________________________________________________________________
@extend_schema(tags=["admin/teacher"])
class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.filter(role='teacher')

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['role'] = 'teacher'
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema(tags=["admin/student"])
class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = User.objects.filter(role='student')

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['role'] = 'student'
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["put"], url_path="group")
    def assign_group(self, request, pk=None):
        student = self.get_object()
        group_id = request.data.get("group")
        if not group_id:
            return Response({"error": "Group ID required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)

        student.group = group
        student.save()
        return Response({"message": f"Student assigned to group {group.name}"})


@extend_schema(tags=["admin/group"])
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    http_method_names = ['get', 'post', 'put', 'delete']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["put"], url_path="teacher")
    def assign_teacher(self, request, pk=None):
        group = self.get_object()
        teacher_id = request.data.get("teacher")
        if not teacher_id:
            return Response({"error": "Teacher ID required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response({"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND)

        group.teacher = teacher
        group.save()
        return Response({"message": f"Teacher {teacher.fullname} assigned to group {group.name}"})

    @action(detail=True, methods=["get"], url_path="leaderboard")
    def leaderboard(self, request, pk=None):
        group = self.get_object()
        submissions = Submission.objects.filter(student__group=group, final_grade__isnull=False)
        scores = {}

        for s in submissions:
            user = s.student
            if user.id not in scores:
                scores[user.id] = {
                    'id': user.id,
                    'fullname': user.fullname,
                    'total_score': 0
                }
            scores[user.id]['total_score'] += s.final_grade

        leaderboard = sorted(scores.values(), key=lambda x: x['total_score'], reverse=True)
        return Response(leaderboard)


# TEACHER VIEWS
# __________________________________________________________________________________________________________________
@extend_schema(tags=["teacher"])
class TeacherHomeworkViewSet(viewsets.ModelViewSet):
    serializer_class = HomeworkSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    http_method_names = ['get', 'post', 'put', 'delete']

    def get_queryset(self):
        return Homework.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


@extend_schema(tags=["teacher"])
class TeacherGroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    http_method_names = ['get']

    def get_queryset(self):
        return Group.objects.filter(teacher=self.request.user)

    @action(methods=['get'], detail=True, url_path='submissions')
    def submissions(self, request, pk=None):
        group = self.get_object()
        submissions = Submission.objects.filter(homework__group=group)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=True, url_path='leaderboard')
    def leaderboard(self, request, pk=None):
        group = self.get_object()
        submissions = Submission.objects.filter(student__group=group, final_grade__isnull=False)
        result = {}
        for submission in submissions:
            student = submission.student
            if student.id not in result:
                result[student.id] = {
                    'student_id': student.id,
                    'full_name': student.fullname,
                    'total_grade': 0
                }
            result[student.id]['total_grade'] += submission.final_grade

        sorted_list = sorted(result.values(), key=lambda x: x['total_grade'], reverse=True)
        return Response(sorted_list)


@extend_schema(tags=["teacher"])
class TeacherSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = SubmissionSerializer
    http_method_names = ['get', 'put']

    def get_queryset(self):
        return Submission.objects.filter(homework__teacher=self.request.user)

    @action(methods=['put'], detail=True, url_path='grade')
    def grade(self, request, pk=None):
        submission = get_object_or_404(Submission, id=pk, homework__teacher=self.request.user)
        grade, created = Grade.objects.get_or_create(submission=submission)
        serializer = GradeSerializer(grade, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(modified_by_teacher=True)
        return Response(serializer.data)


# STUDENT VIEWSETS
# __________________________________________________________________________________________________________________
@extend_schema(tags=["student"])
class StudentHomeworkViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HomeworkSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        if self.request.user.group:
            return Homework.objects.filter(group=self.request.user.group)
        return Homework.objects.none()


@extend_schema(tags=["student"])
class StudentSubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    http_method_names = ['get', 'post']

    def get_queryset(self):
        return Submission.objects.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

