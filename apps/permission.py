from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Permission class to check if user is admin"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsTeacher(BasePermission):
    """Permission class to check if user is teacher"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'teacher'


class IsStudent(BasePermission):
    """Permission class to check if user is student"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'

