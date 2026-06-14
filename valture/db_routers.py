# valture/db_routers.py

import threading

_local = threading.local()

class TenantRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if getattr(_local, 'running_tenant_migration', False):
            # During tenant migration, only migrate workspace_tenant
            return app_label == 'workspace_tenant'
        else:
            # During normal migration, block workspace_tenant
            if app_label == 'workspace_tenant':
                return False
        return None
