import uuid
from django.db import models
from django.conf import settings
from api.workspaces.models import Workspace


class WorkspaceMember(models.Model):
    ROLE_CHOICES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Temporary workspace reference for Phase 1 single-schema simulation
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_memberships'
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workspace_members'
        unique_together = ('workspace', 'user')
        verbose_name = 'Workspace Member'
        verbose_name_plural = 'Workspace Members'

    def __str__(self):
        return f"{self.email} member of {self.workspace.name} ({self.role})"


class WorkspaceInvitation(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Temporary workspace reference for Phase 1 single-schema simulation
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        db_table = 'workspace_invitations'
        unique_together = ('workspace', 'email')
        verbose_name = 'Workspace Invitation'
        verbose_name_plural = 'Workspace Invitations'

    def __str__(self):
        return f"Invite for {self.email} to {self.workspace.name} ({self.role})"
