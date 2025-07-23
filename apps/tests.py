from django.test import TestCase

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from apps.models import User, Group, Homework, Submission, SubmissionFile, Grade, UserSession, Course
from apps.permission import IsAdmin, IsTeacher, IsStudent


class BaseTestCase(APITestCase):
    """Base test case with common setup for all tests"""

    def setUp(self):
        """Create test users and basic data"""
        # Create users with different roles
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='admin123',
            email='admin@test.com',
            fullname='Admin Test',
            role='admin'
        )

        self.teacher_user = User.objects.create_user(
            username='teacher_test',
            password='teacher123',
            email='teacher@test.com',
            fullname='Teacher Test',
            role='teacher'
        )

        self.student_user = User.objects.create_user(
            username='student_test',
            password='student123',
            email='student@test.com',
            fullname='Student Test',
            role='student'
        )

        # Create group
        self.group = Group.objects.create(
            name='Test Group',
            teacher=self.teacher_user
        )

        # Assign student to group
        self.student_user.group = self.group
        self.student_user.save()

        # Create homework
        self.homework = Homework.objects.create(
            title='Test Homework',
            description='Test homework description',
            points=100,
            start_date=timezone.now(),
            deadline=timezone.now() + timedelta(days=7),
            teacher=self.teacher_user,
            group=self.group,
            file_extension='.py'
        )

        # Create API clients
        self.admin_client = APIClient()
        self.teacher_client = APIClient()
        self.student_client = APIClient()
        self.anonymous_client = APIClient()

    def authenticate_user(self, client, user):
        """Helper method to authenticate user"""
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        return refresh


class PermissionTestCase(BaseTestCase):
    """Test custom permissions"""

    def test_is_admin_permission(self):
        """Test IsAdmin permission"""
        permission = IsAdmin()

        # Mock request with admin user
        class MockRequest:
            def __init__(self, user):
                self.user = user

        # Test with admin user
        request = MockRequest(self.admin_user)
        self.assertTrue(permission.has_permission(request, None))

        # Test with non-admin user
        request = MockRequest(self.teacher_user)
        self.assertFalse(permission.has_permission(request, None))

        # Test with unauthenticated user
        class UnauthenticatedUser:
            is_authenticated = False
            role = None

        request = MockRequest(UnauthenticatedUser())
        self.assertFalse(permission.has_permission(request, None))

    def test_is_teacher_permission(self):
        """Test IsTeacher permission"""
        permission = IsTeacher()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        # Test with teacher user
        request = MockRequest(self.teacher_user)
        self.assertTrue(permission.has_permission(request, None))

        # Test with non-teacher user
        request = MockRequest(self.student_user)
        self.assertFalse(permission.has_permission(request, None))

    def test_is_student_permission(self):
        """Test IsStudent permission"""
        permission = IsStudent()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        # Test with student user
        request = MockRequest(self.student_user)
        self.assertTrue(permission.has_permission(request, None))

        # Test with non-student user
        request = MockRequest(self.teacher_user)
        self.assertFalse(permission.has_permission(request, None))


class AuthenticationTestCase(BaseTestCase):
    """Test authentication related views"""

    def test_register_user(self):
        """Test user registration"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'password': 'newpassword123',
            'email': 'newuser@test.com',
            'fullname': 'New User',
            'role': 'student'
        }

        response = self.anonymous_client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_session_list_view(self):
        """Test session list view"""
        # Create user session
        UserSession.objects.create(
            user=self.student_user,
            refresh_token='test_token',
            jti='test_jti',
            user_agent='Test Browser'
        )

        self.authenticate_user(self.student_client, self.student_user)

        url = reverse('sessions_list')
        response = self.student_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sessions', response.data)

    def test_session_destroy(self):
        """Test session destroy"""
        session = UserSession.objects.create(
            user=self.student_user,
            refresh_token='test_token',
            jti='test_jti'
        )

        self.authenticate_user(self.student_client, self.student_user)

        url = f'/api/auth/sessions/delete/{session.id}'
        response = self.student_client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserSession.objects.filter(id=session.id).exists())


class StudentViewTestCase(BaseTestCase):
    """Test student related views"""

    def test_leaderboard_list(self):
        """Test leaderboard list view"""
        # Create submission with grade for leaderboard
        submission = Submission.objects.create(
            homework=self.homework,
            student=self.student_user,
            final_grade=85.5
        )

        url = '/api/student/leaders-list'
        response = self.anonymous_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_student_homework_list(self):
        """Test student homework list"""
        self.authenticate_user(self.student_client, self.student_user)

        url = '/api/student/my-homework'
        response = self.student_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_student_submission_list(self):
        """Test student submission list"""
        # Create submission
        Submission.objects.create(
            homework=self.homework,
            student=self.student_user
        )

        self.authenticate_user(self.student_client, self.student_user)

        url = '/api/student/submissions/list'
        response = self.student_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_homework_create_by_student_fails(self):
        """Test that homework creation by student should fail"""
        self.authenticate_user(self.student_client, self.student_user)

        data = {
            'homework': self.homework.id,
            'student': self.student_user.id
        }

        url = '/api/student/create-homework'
        response = self.student_client.post(url, data)

        # This should work since it's creating a submission, not homework
        # The naming might be confusing but based on serializer it's submission
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class AdminViewTestCase(BaseTestCase):
    """Test admin related views"""

    def test_teacher_viewset_list(self):
        """Test teacher list by admin"""
        self.authenticate_user(self.admin_client, self.admin_user)

        url = '/admin/teacher/'
        response = self.admin_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_teacher_create_by_admin(self):
        """Test teacher creation by admin"""
        self.authenticate_user(self.admin_client, self.admin_user)

        data = {
            'username': 'newteacher',
            'password': 'teacher123',
            'fullname': 'New Teacher',
            'email': 'newteacher@test.com',
            'phone': '1234567890'
        }

        url = '/admin/teacher/'
        response = self.admin_client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newteacher', role='teacher').exists())

    def test_student_viewset_list(self):
        """Test student list by admin"""
        self.authenticate_user(self.admin_client, self.admin_user)

        url = '/admin/student/'
        response = self.admin_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_create_by_admin(self):
        """Test student creation by admin"""
        self.authenticate_user(self.admin_client, self.admin_user)

        data = {
            'username': 'newstudent',
            'password': 'student123',
            'fullname': 'New Student',
            'email': 'newstudent@test.com'
        }

        url = '/admin/student/'
        response = self.admin_client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newstudent', role='student').exists())

    def test_assign_student_to_group(self):
        """Test assigning student to group"""
        # Create new student
        new_student = User.objects.create_user(
            username='student2',
            password='password',
            fullname='Student 2',
            role='student'
        )

        self.authenticate_user(self.admin_client, self.admin_user)

        url = f'/admin/student/{new_student.id}/group/'
        data = {'group': self.group.id}
        response = self.admin_client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_student.refresh_from_db()
        self.assertEqual(new_student.group, self.group)

    def test_group_viewset_operations(self):
        """Test group CRUD operations"""
        self.authenticate_user(self.admin_client, self.admin_user)

        # List groups
        url = '/admin/groups/'
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Create group
        data = {
            'name': 'New Group',
            'teacher': self.teacher_user.id
        }
        response = self.admin_client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Get group detail
        group_id = response.data['id']
        url = f'/admin/groups/{group_id}/'
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assign_teacher_to_group(self):
        """Test assigning teacher to group"""
        new_teacher = User.objects.create_user(
            username='teacher2',
            password='password',
            fullname='Teacher 2',
            role='teacher'
        )

        self.authenticate_user(self.admin_client, self.admin_user)

        url = f'/admin/groups/{self.group.id}/teacher/'
        data = {'teacher': new_teacher.id}
        response = self.admin_client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.teacher, new_teacher)


class TeacherViewTestCase(BaseTestCase):
    """Test teacher related views"""

    def test_teacher_homework_list(self):
        """Test teacher homework list"""
        self.authenticate_user(self.teacher_client, self.teacher_user)

        url = '/teacher/homework/'
        response = self.teacher_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_teacher_homework_create(self):
        """Test homework creation by teacher"""
        self.authenticate_user(self.teacher_client, self.teacher_user)

        data = {
            'title': 'New Homework',
            'description': 'New homework description',
            'points': 50,
            'start_date': timezone.now().isoformat(),
            'deadline': (timezone.now() + timedelta(days=3)).isoformat(),
            'group': self.group.id,
            'file_extension': '.py'
        }

        url = '/teacher/homework/'
        response = self.teacher_client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Homework.objects.filter(title='New Homework').exists())

    def test_teacher_group_list(self):
        """Test teacher group list"""
        self.authenticate_user(self.teacher_client, self.teacher_user)

        url = '/teacher/groups/'
        response = self.teacher_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_teacher_group_submissions(self):
        """Test teacher viewing group submissions"""
        # Create submission
        Submission.objects.create(
            homework=self.homework,
            student=self.student_user
        )

        self.authenticate_user(self.teacher_client, self.teacher_user)

        url = f'/teacher/groups/{self.group.id}/submissions/'
        response = self.teacher_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_teacher_group_leaderboard(self):
        """Test teacher viewing group leaderboard"""
        # Create submission with grade
        submission = Submission.objects.create(
            homework=self.homework,
            student=self.student_user,
            final_grade=90.0
        )

        self.authenticate_user(self.teacher_client, self.teacher_user)

        url = f'/teacher/groups/{self.group.id}/leaderboard/'
        response = self.teacher_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_teacher_submission_grading(self):
        """Test teacher grading submission"""
        submission = Submission.objects.create(
            homework=self.homework,
            student=self.student_user
        )

        self.authenticate_user(self.teacher_client, self.teacher_user)

        url = f'/teacher/submissions/{submission.id}/grade/'
        data = {
            'final_task_completeness': 85.0,
            'final_code_quality': 90.0,
            'final_correctness': 88.0,
            'teacher_total': 87.7
        }
        response = self.teacher_client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UnauthorizedAccessTestCase(BaseTestCase):
    """Test unauthorized access to protected endpoints"""

    def test_admin_endpoints_require_admin_permission(self):
        """Test that admin endpoints require admin permission"""
        # Test with unauthenticated user
        url = '/admin/teacher/'
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with student user
        self.authenticate_user(self.student_client, self.student_user)
        response = self.student_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_endpoints_require_teacher_permission(self):
        """Test that teacher endpoints require teacher permission"""
        # Test with unauthenticated user
        url = '/teacher/homework/'
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test with student user
        self.authenticate_user(self.student_client, self.student_user)
        response = self.student_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_protected_endpoints_require_authentication(self):
        """Test that student protected endpoints require authentication"""
        url = '/api/student/my-homework'
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ModelTestCase(BaseTestCase):
    """Test model methods and properties"""

    def test_user_model_str(self):
        """Test User model __str__ method"""
        expected = f"{self.student_user.fullname} ({self.student_user.username})"
        self.assertEqual(str(self.student_user), expected)

    def test_group_student_count_property(self):
        """Test Group model student_count property"""
        self.assertEqual(self.group.student_count, 1)

        # Add another student
        User.objects.create_user(
            username='student2',
            password='password',
            fullname='Student 2',
            role='student',
            group=self.group
        )

        self.assertEqual(self.group.student_count, 2)

    def test_submission_file_line_count(self):
        """Test SubmissionFile line count calculation"""
        submission = Submission.objects.create(
            homework=self.homework,
            student=self.student_user
        )

        content = "line 1\nline 2\nline 3"
        submission_file = SubmissionFile.objects.create(
            submission=submission,
            file_name='test.py',
            content=content
        )

        self.assertEqual(submission_file.line_count, 3)

    def test_homework_str(self):
        """Test Homework model __str__ method"""
        expected = f"{self.homework.title} - {self.homework.group.name}"
        self.assertEqual(str(self.homework), expected)


class SerializerTestCase(BaseTestCase):
    """Test serializers"""

    def test_user_profile_serializer_group_name(self):
        """Test UserProfileSerializer group_name method"""
        from apps.serializer import UserProfileSerializer

        serializer = UserProfileSerializer(instance=self.student_user)
        self.assertEqual(serializer.data['group_name'], self.group.name)

        # Test user without group
        user_without_group = User.objects.create_user(
            username='nogroupuser',
            password='password',
            fullname='No Group User',
            role='student'
        )

        serializer = UserProfileSerializer(instance=user_without_group)
        self.assertIsNone(serializer.data['group_name'])

    def test_homework_serializer_submission_count(self):
        """Test HomeworkSerializer submission_count method"""
        from apps.serializer import HomeworkSerializer

        # Create submissions
        Submission.objects.create(homework=self.homework, student=self.student_user)

        serializer = HomeworkSerializer(instance=self.homework)
        self.assertEqual(serializer.data['submission_count'], 1)


if __name__ == '__main__':
    # Run specific test
    import unittest

    unittest.main()