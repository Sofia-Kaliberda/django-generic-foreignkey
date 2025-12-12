# action_logs/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import ActionLog, Blog, Comment, UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def log_user_save(sender, instance, created, **kwargs):
    action_type = 'create' if created else 'update'
    ip_address = None
    user_agent = ''
    
    try:
        from django.http import HttpRequest
        request = HttpRequest()
    except:
        pass
    
    ActionLog.objects.create(
        action_type=action_type,
        user=instance,
        content_object=instance,
        description=f'{action_type.capitalize()} користувача: {instance.username}',
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    logger.info(f"Записано лог для користувача {instance.username}: {action_type}")


@receiver(post_save, sender=UserProfile)
def log_profile_save(sender, instance, created, **kwargs):
    action_type = 'create' if created else 'update'
    
    ActionLog.objects.create(
        action_type=action_type,
        user=instance.user,
        content_object=instance,
        description=f'{action_type.capitalize()} профілю {instance.user.username}'
    )

@receiver(post_save, sender=Blog)
def log_blog_save(sender, instance, created, **kwargs):
    if created:
        return
    
    instance.log_action(
        user=instance.author,
        action_type='update',
        description=f'Оновлено блог: {instance.title}'
    )


@receiver(post_delete, sender=Blog)
def log_blog_delete(sender, instance, **kwargs):
    ActionLog.objects.create(
        action_type='delete',
        user=instance.author,
        description=f'Видалено блог: {instance.title}',
        )


@receiver(post_save, sender=Comment)
def log_comment_save(sender, instance, created, **kwargs):

    if created:
        return
    
    instance.log_action(
        user=instance.author,
        action_type='update',
        description=f'Оновлено коментар до "{instance.blog.title}"'
    )


@receiver(post_delete, sender=Comment)
def log_comment_delete(sender, instance, **kwargs):
    ActionLog.objects.create(
        action_type='delete',
        user=instance.author,
        description=f'Видалено коментар до "{instance.blog.title}"'
    )


@receiver(post_save)
def universal_log_save(sender, instance, created, **kwargs):
    ignored_models = [ActionLog, ContentType]
    
    if sender in ignored_models:
        return
    if hasattr(instance, 'action_logs'):
        return

def register_model_signals(model_class):

    @receiver(post_save, sender=model_class)
    def log_model_save(sender, instance, created, **kwargs):
        action_type = 'create' if created else 'update'
        
        user = None
        if hasattr(instance, 'author'):
            user = instance.author
        elif hasattr(instance, 'user'):
            user = instance.user
        elif hasattr(instance, 'created_by'):
            user = instance.created_by
        
        ActionLog.objects.create(
            action_type=action_type,
            user=user,
            content_object=instance,
            description=f'{action_type.capitalize()} {model_class.__name__}: {str(instance)[:100]}'
        )