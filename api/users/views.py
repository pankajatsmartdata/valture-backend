from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSignupSerializer, UserSerializer, CustomTokenObtainPairSerializer
from api.workspaces.models import UserWorkspaceMapping, Workspace

User = get_user_model()
signer = TimestampSigner()
reset_signer = TimestampSigner(salt='password-reset')


class SignupView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate email verification token
            token = signer.sign(user.email)
            verify_url = f"{settings.FRONTEND_URL}/api/auth/verify/?token={token}"

            # Send (log to console) the verification link
            send_mail(
                subject="Verify your email - Valture",
                message=f"Please verify your email by clicking the following link: {verify_url}",
                from_email=settings.GMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            return Response(
                {"message": "User registered successfully. Please check your email for the verification link."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Token is valid for 24 hours (86400 seconds)
            email = signer.unsign(token, max_age=86400)
            user = User.objects.get(email=email)
            if not user.is_verified:
                user.is_verified = True
                user.is_active = True
                user.save()
            return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)
        except SignatureExpired:
            return Response({"error": "Verification token has expired"}, status=status.HTTP_400_BAD_REQUEST)
        except (BadSignature, User.DoesNotExist):
            return Response({"error": "Invalid verification token"}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class SwitchWorkspaceView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        workspace_id = request.data.get("workspace_id")
        if not workspace_id:
            return Response({"error": "workspace_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            mapping = UserWorkspaceMapping.objects.get(
                user=request.user,
                workspace_id=workspace_id
            )
        except (UserWorkspaceMapping.DoesNotExist, ValueError):
            return Response(
                {"error": "You are not a member of this workspace or workspace does not exist"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Regenerate JWT tokens with the new active workspace embedded
        refresh = RefreshToken.for_user(request.user)
        refresh['workspace_id'] = str(mapping.workspace.id)
        refresh['role'] = mapping.role
        
        access_token = refresh.access_token
        access_token['workspace_id'] = str(mapping.workspace.id)
        access_token['role'] = mapping.role

        # Get list of workspaces user belongs to
        mappings = request.user.workspace_mappings.select_related('workspace').all()
        workspaces_list = []
        for m in mappings:
            workspaces_list.append({
                'id': str(m.workspace.id),
                'name': m.workspace.name,
                'slug': m.workspace.slug,
                'role': m.role
            })

        return Response({
            "refresh": str(refresh),
            "access": str(access_token),
            "active_workspace": {
                "id": str(mapping.workspace.id),
                "name": mapping.workspace.name,
                "slug": mapping.workspace.slug,
                "role": mapping.role
            },
            "workspaces": workspaces_list
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            # Generate reset token
            token = reset_signer.sign(user.email)
            reset_url = f"{settings.FRONTEND_URL}/api/auth/password-reset-confirm/?token={token}"
            
            # Send (log to console) reset link
            send_mail(
                subject="Password Reset - Valture",
                message=f"Reset your password using the following link: {reset_url}",
                from_email="noreply@valture.com",
                recipient_list=[user.email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            # Silently return success to prevent email enumeration attacks
            pass
        
        return Response(
            {"message": "If the email exists, a password reset link has been sent."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        token = request.data.get("token")
        password = request.data.get("password")
        
        if not token or not password:
            return Response({"error": "Token and password are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Token is valid for 1 hour
            email = reset_signer.unsign(token, max_age=3600)
            user = User.objects.get(email=email)
            
            # Validate password strength
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            try:
                validate_password(password, user)
            except ValidationError as e:
                return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(password)
            user.save()
            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        except SignatureExpired:
            return Response({"error": "Password reset token has expired"}, status=status.HTTP_400_BAD_REQUEST)
        except (BadSignature, User.DoesNotExist):
            return Response({"error": "Invalid password reset token"}, status=status.HTTP_400_BAD_REQUEST)
