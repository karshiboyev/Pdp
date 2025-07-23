from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from .models import User, Session, Group, Homework, Submission, SubmissionFile, Grade, Course


class RegisterSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'fullname', 'username', 'email', 'password', 'phone', 'role', 'group', 'created_at')
        read_only_fields = ('created_at', 'id')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(ModelSerializer):
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'fullname', 'username', 'email', 'phone', 'role', 'group', 'group_name', 'created_at')
        read_only_fields = ('created_at', 'id')

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None


class TeacherSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'fullname', 'phone', 'email', 'role', 'created_at']
        read_only_fields = ['id', 'created_at', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        user.role = 'teacher'
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.role = 'teacher'
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class StudentSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'fullname', 'phone', 'email', 'group', 'group_name', 'role',
                  'created_at']
        read_only_fields = ['id', 'created_at', 'role']

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        user.role = 'student'
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.role = 'student'
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class GroupSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    student_count = serializers.ReadOnlyField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'teacher', 'teacher_name', 'student_count', 'created_at']
        read_only_fields = ['student_count']

    def get_teacher_name(self, obj):
        return obj.teacher.fullname if obj.teacher else None

    def get_course_name(self, obj):
        return obj.course.name if obj.course else None


class SessionSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = ['id', 'user', 'username', 'token', 'device_name', 'ip_address', 'last_login', 'expires_at']

    def get_username(self, obj):
        return obj.user.username


class HomeworkSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    is_submitted = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = ['id', 'title', 'description', 'points', 'start_date', 'deadline',
                  'line_limit', 'teacher', 'teacher_name', 'group', 'group_name',
                  'file_extension', 'ai_grading_prompt', 'submission_count', 'is_submitted', 'created_at']
        read_only_fields = ['teacher', 'submission_count', 'is_submitted']

    def get_teacher_name(self, obj):
        return obj.teacher.fullname

    def get_group_name(self, obj):
        return obj.group.name

    def get_submission_count(self, obj):
        return obj.submissions.count()

    def get_is_submitted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.submissions.filter(student=request.user).exists()
        return False


class SubmissionFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionFile
        fields = ['id', 'file_name', 'content', 'line_count']


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = ['submission']


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    homework_title = serializers.SerializerMethodField()
    files = SubmissionFileSerializer(many=True, read_only=True)
    grade = GradeSerializer(read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'homework', 'homework_title', 'student', 'student_name',
                  'submitted_at', 'ai_grade', 'final_grade', 'ai_feedback',
                  'files', 'grade', 'created_at']
        read_only_fields = ['student', 'submitted_at', 'ai_grade', 'ai_feedback', 'created_at']

    def get_student_name(self, obj):
        return obj.student.fullname

    def get_homework_title(self, obj):
        return obj.homework.title


class UserSerializer(serializers.ModelSerializer):
    total_score = serializers.DecimalField(max_digits=10, decimal_places=2)
    rank = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'fullname', 'total_score', 'rank']

    def get_rank(self, obj):
        queryset = self.context['view'].get_queryset()
        ordered_ids = list(queryset.values_list('id', flat=True))
        return ordered_ids.index(obj.id) + 1


# Fixed CreateHomeworkSerializer - was using wrong model
class CreateSubmissionSerializer(ModelSerializer):
    student_name = SerializerMethodField()

    class Meta:
        model = Submission
        fields = (
            'homework', 'student',
            'ai_grade', 'ai_feedback', 'student_name'
        )

    def get_student_name(self, obj):
        return obj.student.fullname  # Fixed: was using full_name instead of fullname
