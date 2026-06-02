# foto_config/routers.py

class FotoConfigRouter:
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'default':
            return app_label == 'app_foto_config'
        return None