from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.signing import TimestampSigner
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase

from api.workspaces.models import Workspace, UserWorkspaceMapping
from api.workspace_tenant.models import WorkspaceMember, WorkspaceInvitation

User = get_user_model()
signer = TimestampSigner()
reset_signer = TimestampSigner(salt='password-reset')


class AuthenticationTests(APITestCase):

    def setUp(self):
        self.signup_url = reverse('auth-signup')
        self.verify_url = reverse('auth-verify')
        self.login_url = reverse('auth-login')
        self.profile_url = reverse('users-profile')
        self.switch_workspace_url = reverse('auth-switch-workspace')
        self.password_reset_request_url = reverse('auth-password-reset-request')
        self.password_reset_confirm_url = reverse('auth-password-reset-confirm')

        self.user_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }

    def test_user_signup_creates_default_workspace(self):
        response = self.client.post(self.signup_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("User registered successfully", response.data['message'])

        # Check user created
        user = User.objects.get(email=self.user_data['email'])
        self.assertFalse(user.is_verified)

        # Check default workspace created
        self.assertEqual(Workspace.objects.count(), 1)
        workspace = Workspace.objects.first()
        self.assertEqual(workspace.name, "Test's Workspace")

        # Check mapping and member
        self.assertTrue(UserWorkspaceMapping.objects.filter(user=user, workspace=workspace, role='owner').exists())
        from api.workspaces.schema_manager import set_search_path, reset_search_path
        try:
            set_search_path(workspace.schema_name)
            self.assertTrue(WorkspaceMember.objects.filter(user=user, role='owner').exists())
        finally:
            reset_search_path()

        # Check email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify your email", mail.outbox[0].subject)

    def test_user_signup_with_custom_workspace(self):
        data = self.user_data.copy()
        data['workspace_name'] = 'Custom Business'
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        workspace = Workspace.objects.get(name='Custom Business')
        self.assertEqual(workspace.slug, 'custom-business')

    def test_email_verification(self):
        # Signup user
        self.client.post(self.signup_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        self.assertFalse(user.is_verified)

        # Generate token and verify
        token = signer.sign(user.email)
        response = self.client.get(f"{self.verify_url}?token={token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_email_verification_invalid_token(self):
        response = self.client.get(f"{self.verify_url}?token=invalid-token")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_login_returns_jwt_with_workspace_context(self):
        # Register and verify user
        self.client.post(self.signup_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.is_verified = True
        user.save()

        # Login
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('active_workspace', response.data)
        self.assertIsNotNone(response.data['active_workspace'])
        self.assertEqual(response.data['active_workspace']['role'], 'owner')
        self.assertEqual(len(response.data['workspaces']), 1)

    def test_profile_retrieval_and_update(self):
        # Register and verify
        self.client.post(self.signup_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.is_verified = True
        user.save()

        # Login to get token
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Get profile
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Test')

        # Patch profile
        patch_response = self.client.patch(self.profile_url, {'first_name': 'UpdatedName'})
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['first_name'], 'UpdatedName')

    def test_workspace_switching_and_jwt_regeneration(self):
        # Register & verify
        self.client.post(self.signup_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.is_verified = True
        user.save()

        # Login to authenticate
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        })
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Create a second workspace
        second_ws_response = self.client.post(reverse('workspaces-list-create'), {'name': 'Second Workspace'})
        self.assertEqual(second_ws_response.status_code, status.HTTP_201_CREATED)
        second_ws_id = second_ws_response.data['id']

        # Switch to the second workspace
        switch_response = self.client.post(self.switch_workspace_url, {'workspace_id': second_ws_id})
        self.assertEqual(switch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(switch_response.data['active_workspace']['id'], second_ws_id)
        self.assertEqual(switch_response.data['active_workspace']['name'], 'Second Workspace')
        
        # Verify user has 2 workspaces in response
        self.assertEqual(len(switch_response.data['workspaces']), 2)

    def test_password_reset_flow(self):
        self.client.post(self.signup_url, self.user_data)
        
        # Request password reset
        mail.outbox = []
        request_response = self.client.post(self.password_reset_request_url, {'email': self.user_data['email']})
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        # Extract token from the email body
        email_body = mail.outbox[0].body
        token = email_body.split("token=")[1].strip()

        # Confirm password reset
        confirm_response = self.client.post(self.password_reset_confirm_url, {
            'token': token,
            'password': 'NewSecurePassword123!'
        })
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Login with new password
        login_response = self.client.post(self.login_url, {
            'email': self.user_data['email'],
            'password': 'NewSecurePassword123!'
        })
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)


class WorkspaceTenantTests(APITestCase):

    def setUp(self):
        self.signup_url = reverse('auth-signup')
        self.login_url = reverse('auth-login')

        # Create user A
        self.user_a_data = {'email': 'a@example.com', 'password': 'Password123!', 'first_name': 'A'}
        self.client.post(self.signup_url, self.user_a_data)
        self.user_a = User.objects.get(email='a@example.com')
        self.user_a.is_verified = True
        self.user_a.save()

        # Create user B
        self.user_b_data = {'email': 'b@example.com', 'password': 'Password123!', 'first_name': 'B'}
        self.client.post(self.signup_url, self.user_b_data)
        self.user_b = User.objects.get(email='b@example.com')
        self.user_b.is_verified = True
        self.user_b.save()

        # Authenticate as user A
        login_res = self.client.post(self.login_url, {'email': 'a@example.com', 'password': 'Password123!'})
        self.token_a = login_res.data['access']
        self.workspace_a_id = login_res.data['active_workspace']['id']

    def test_invite_member_and_join_workspace(self):
        # Authenticate as User A
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')

        # Invite user B
        invite_url = reverse('workspace-invite', kwargs={'workspace_id': self.workspace_a_id})
        mail.outbox = []
        invite_response = self.client.post(invite_url, {'email': 'b@example.com', 'role': 'member'})
        self.assertEqual(invite_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)

        # Get token from email
        token = mail.outbox[0].body.split("token=")[1].strip()

        # Authenticate as User B
        login_res = self.client.post(self.login_url, {'email': 'b@example.com', 'password': 'Password123!'})
        token_b = login_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_b}')

        # Join the workspace
        join_url = reverse('workspace-join', kwargs={'workspace_id': self.workspace_a_id})
        join_response = self.client.post(join_url, {'token': token})
        self.assertEqual(join_response.status_code, status.HTTP_200_OK)

        # Verify User B has access to workspace A
        workspaces_response = self.client.get(reverse('workspaces-list-create'))
        self.assertEqual(workspaces_response.status_code, status.HTTP_200_OK)
        # Should be member of their own default workspace AND workspace A
        self.assertEqual(len(workspaces_response.data), 2)
        
        # Check that user B is in workspace members list
        members_url = reverse('workspace-members-list', kwargs={'workspace_id': self.workspace_a_id})
        members_response = self.client.get(members_url)
        self.assertEqual(members_response.status_code, status.HTTP_200_OK)
        emails = [m['email'] for m in members_response.data]
        self.assertIn('b@example.com', emails)
        self.assertIn('a@example.com', emails)
