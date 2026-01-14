import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


class ActionLog(models.Model):

    ACTION_TYPES = [
        ('create', 'Створення'),
        ('update', 'Оновлення'),
        ('delete', 'Видалення'),
        ('view', 'Перегляд'),
        ('login', 'Вхід'),
        ('logout', 'Вихід'),
        ('download', 'Завантаження'),
        ('upload', 'Завантаження'),
        ('share', 'Поділитися'),
        ('other', 'Інша дія'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='Ідентифікатор'
    )
    
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name='Тип дії'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата та час'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='action_logs',
        verbose_name='Користувач'
    )
    

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Тип вмісту'
    )
    
    object_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='ID об\'єкта'
    )
    
    content_object = GenericForeignKey(
        'content_type',
        'object_id'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Опис'
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP адреса'
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    
    class Meta:
        verbose_name = 'Лог дії'
        verbose_name_plural = 'Логи дій'
        ordering = ['-timestamp']

        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['action_type']),
            models.Index(fields=['user']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Анонім'
        action = self.get_action_type_display()
        
        if self.content_object:
            obj_str = str(self.content_object)[:50]
            return f"{action} | {user_str} | {obj_str}"
        return f"{action} | {user_str} | {self.timestamp}"
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('action_log_detail', args=[str(self.id)])
    
    @property
    def object_type(self):
        if self.content_type:
            return self.content_type.model_class().__name__
        return 'Немає'
    
    @classmethod
    def log_action(cls, user, action_type, obj=None, description='', 
                   ip_address=None, user_agent=''):

        log = cls.objects.create(
            user=user,
            action_type=action_type,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if obj:
            log.content_object = obj
            log.save()
        
        return log


class LoggedModel(models.Model):
    action_logs = GenericRelation(
        ActionLog,
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='%(app_label)s_%(class)s'
    )
    
    class Meta:
        abstract = True
    
    def get_action_logs(self):
        return self.action_logs.all()
    
    def get_recent_logs(self, limit=10):
        return self.action_logs.all()[:limit]
    
    def log_action(self, user, action_type, description='', 
                   ip_address=None, user_agent=''):
        return ActionLog.log_action(
            user=user,
            action_type=action_type,
            obj=self,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )


class Blog(LoggedModel):

    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок'
    )
    
    content = models.TextField(
        verbose_name='Зміст'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blogs',
        verbose_name='Автор'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Створено'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Оновлено'
    )
    
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубліковано'
    )
    
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Теги'
    )
    
    class Meta:
        verbose_name = 'Блог'
        verbose_name_plural = 'Блоги'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        if is_new:
            self.log_action(
                user=self.author,
                action_type='create',
                description=f'Створено блог: {self.title}'
            )
        else:
            self.log_action(
                user=self.author,
                action_type='update',
                description=f'Оновлено блог: {self.title}'
            )
    
    def delete(self, *args, **kwargs):
        self.log_action(
            user=self.author,
            action_type='delete',
            description=f'Видалено блог: {self.title}'
        )
        super().delete(*args, **kwargs)


class Comment(LoggedModel):
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Блог'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    
    text = models.TextField(
        verbose_name='Текст коментаря'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Створено'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Оновлено'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активний'
    )
    
    class Meta:
        verbose_name = 'Коментар'
        verbose_name_plural = 'Коментарі'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Коментар від {self.author} до "{self.blog.title}"'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.log_action(
                user=self.author,
                action_type='create',
                description=f'Додано коментар до блогу: {self.blog.title}'
            )
    
    @property
    def preview(self):
        return self.text[:100] + '...' if len(self.text) > 100 else self.text


class UserProfile(LoggedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Користувач'
    )
    
    bio = models.TextField(
        blank=True,
        verbose_name='Біографія'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )
    
    website = models.URLField(
        blank=True,
        verbose_name='Веб-сайт'
    )
    
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Місцезнаходження'
    )
    
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата народження'
    )
    
    social_links = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Соціальні мережі'
    )
    
    class Meta:
        verbose_name = 'Профіль'
        verbose_name_plural = 'Профілі'
    
    def __str__(self):
        return f'Профіль {self.user.username}'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.log_action(
                user=self.user,
                action_type='create',
                description=f'Створено профіль для {self.user.username}'
            )
        else:
            self.log_action(
                user=self.user,
                action_type='update',
                description=f'Оновлено профіль {self.user.username}'
            )