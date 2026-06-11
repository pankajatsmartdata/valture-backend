import uuid
from django.db import models
from django.conf import settings


class WorkspaceMember(models.Model):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships',
        unique=True
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'workspace_members'
        verbose_name = 'Workspace Member'
        verbose_name_plural = 'Workspace Members'

    def __str__(self):
        return f"{self.email} ({self.role})"


class WorkspaceInvitation(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'workspace_invitations'
        verbose_name = 'Workspace Invitation'
        verbose_name_plural = 'Workspace Invitations'

    def __str__(self):
        return f"Invite for {self.email} ({self.role})"
