import re
from django.utils.text import slugify


def generate_unique_slug(name):
    base_slug = slugify(name) or "workspace"
    slug = base_slug
    counter = 1
    from api.workspaces.models import Workspace
    while Workspace.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def generate_unique_schema_name(slug):
    # Standardize to only alphanumeric and underscores
    clean_slug = re.sub(r'[^a-zA-Z0-9_]', '_', slug).lower()
    # Strip leading numbers or underscores to make it a valid schema identifier
    clean_slug = re.sub(r'^[^a-z]+', '', clean_slug) or "tenant"
    schema_name = f"tenant_{clean_slug}"
    # Keep length well below 63 character postgres limit
    schema_name = schema_name[:50]
    
    from api.workspaces.models import Workspace
    base_schema_name = schema_name
    counter = 1
    while Workspace.objects.filter(schema_name=schema_name).exists():
        suffix = f"_{counter}"
        schema_name = base_schema_name[:(63 - len(suffix))] + suffix
        counter += 1
    return schema_name
