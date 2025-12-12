# action_logs/apps.py
from django.apps import AppConfig


class ActionLogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'action_logs'
    verbose_name = 'Логування дій'
    
    def ready(self):
        import action_logs.signals