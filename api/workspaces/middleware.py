from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from api.workspaces.models import Workspace
from api.workspaces.schema_manager import set_search_path, reset_search_path

class WorkspaceSchemaMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.workspace_schema = 'public'
        
        try:
            jwt_authenticator = JWTAuthentication()
            header = jwt_authenticator.get_header(request)
            if header is not None:
                raw_token = jwt_authenticator.get_raw_token(header)
                if raw_token is not None:
                    validated_token = jwt_authenticator.get_validated_token(raw_token)
                    user = jwt_authenticator.get_user(validated_token)
                    
                    workspace_id = validated_token.get('workspace_id')
                    if workspace_id:
                        cache_key = f"workspace_schema_{workspace_id}"
                        schema_name = cache.get(cache_key)
                        if not schema_name:
                            workspace = Workspace.objects.filter(id=workspace_id).first()
                            if workspace:
                                schema_name = workspace.schema_name
                                cache.set(cache_key, schema_name, 3600)
                        
                        if schema_name:
                            request.workspace_schema = schema_name
                            set_search_path(schema_name)
                            request.user = user
                            return
        except Exception:
            pass
        
        reset_search_path()

    def process_response(self, request, response):
        reset_search_path()
        return response
