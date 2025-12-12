# action_logs/admin.py
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.urls import reverse
from .models import ActionLog, Blog, Comment, UserProfile


class ActionLogInline(GenericTabularInline):
    model = ActionLog
    extra = 0
    max_num = 10
    can_delete = False
    readonly_fields = ['action_type', 'timestamp', 'user', 'description', 'ip_address', 'link_to_object']
    
    def link_to_object(self, obj):
        if not obj.content_object:
            return "-"
        try:
            url = reverse(f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change', args=[obj.object_id])
            return format_html('<a href="{}">{}</a>', url, str(obj.content_object)[:50])
        except:
            return str(obj.content_object)[:50]
    
    link_to_object.short_description = "Об'єкт"
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ['action_type_icon', 'timestamp', 'user_link', 'object_link', 'short_description', 'ip_address']
    list_filter = ['action_type', 'timestamp', 'user', 'content_type']
    search_fields = ['description', 'user__username', 'user__email', 'ip_address', 'user_agent']
    readonly_fields = ['id', 'timestamp', 'content_type', 'object_id', 'content_object_link', 'user_link', 'full_description', 'ip_address', 'user_agent_display']
    fieldsets = (
        ('Основна інформація', {'fields': ('id', 'timestamp', 'action_type', 'user_link')}),
        ('Об\'єкт', {'fields': ('content_type', 'object_id', 'content_object_link')}),
        ('Додатково', {'fields': ('full_description', 'ip_address', 'user_agent_display')}),
    )
    list_per_page = 50
    actions = ['export_as_json']
    
    def action_type_icon(self, obj):
        icons = {'create': '📝', 'update': '🔄', 'delete': '🗑️', 'view': '👁️', 'login': '🔑', 'logout': '🚪', 'download': '⬇️', 'upload': '⬆️', 'share': '📤', 'other': '⚙️'}
        icon = icons.get(obj.action_type, '❓')
        return format_html('<span title="{}">{} {}</span>', obj.get_action_type_display(), icon, obj.get_action_type_display())
    
    action_type_icon.short_description = 'Дія'
    
    def user_link(self, obj):
        if not obj.user:
            return "Анонім"
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    
    user_link.short_description = 'Користувач'
    
    def object_link(self, obj):
        if not obj.content_object:
            return "-"
        try:
            url = reverse(f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change', args=[obj.object_id])
            obj_str = str(obj.content_object)[:40]
            return format_html('<a href="{}" title="{}">{} ({})</a>', url, str(obj.content_object), obj_str, obj.content_type.model)
        except:
            return f"{obj.content_type.model}: {obj.object_id}"
    
    object_link.short_description = "Об'єкт"
    
    def short_description(self, obj):
        return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description
    
    short_description.short_description = 'Опис'
    
    def content_object_link(self, obj):
        return self.object_link(obj)
    
    content_object_link.short_description = "Посилання на об'єкт"
    
    def full_description(self, obj):
        return obj.description
    
    full_description.short_description = 'Повний опис'
    
    def user_agent_display(self, obj):
        if not obj.user_agent:
            return "-"
        ua = obj.user_agent.lower()
        if 'chrome' in ua: browser = 'Chrome'
        elif 'firefox' in ua: browser = 'Firefox'
        elif 'safari' in ua: browser = 'Safari'
        elif 'edge' in ua: browser = 'Edge'
        elif 'opera' in ua: browser = 'Opera'
        else: browser = 'Інший'
        return format_html('<div title="{}"><strong>{}</strong><br><small>{}</small></div>', obj.user_agent, browser, obj.user_agent[:100] + '...' if len(obj.user_agent) > 100 else obj.user_agent)
    
    user_agent_display.short_description = 'Браузер'
    
    def export_as_json(self, request, queryset):
        import json
        from django.http import HttpResponse
        data = []
        for log in queryset:
            data.append({
                'id': str(log.id),
                'action_type': log.action_type,
                'timestamp': log.timestamp.isoformat(),
                'user': log.user.username if log.user else None,
                'object_type': log.content_type.model if log.content_type else None,
                'object_id': log.object_id,
                'description': log.description,
                'ip_address': log.ip_address,
            })
        response = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="action_logs.json"'
        return response
    
    export_as_json.short_description = "Експортувати вибрані логи у JSON"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at', 'updated_at', 'is_published', 'action_logs_count']
    list_filter = ['is_published', 'created_at', 'author']
    search_fields = ['title', 'content', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'action_logs_count_display']
    fieldsets = (
        ('Основна інформація', {'fields': ('title', 'content', 'author', 'tags')}),
        ('Налаштування', {'fields': ('is_published',)}),
        ('Метадані', {'fields': ('created_at', 'updated_at', 'action_logs_count_display'), 'classes': ('collapse',)}),
    )
    inlines = [ActionLogInline]
    
    def action_logs_count(self, obj):
        return obj.action_logs.count()
    
    action_logs_count.short_description = 'Логи'
    
    def action_logs_count_display(self, obj):
        count = obj.action_logs.count()
        if count == 0:
            return "Немає логів"
        content_type = ContentType.objects.get_for_model(Blog)
        url = reverse('admin:action_logs_actionlog_changelist')
        url += f'?content_type__id__exact={content_type.id}&object_id__exact={obj.id}'
        return format_html('<a href="{}">{} записів</a>', url, count)
    
    action_logs_count_display.short_description = 'Історія дій'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['preview', 'author', 'blog', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'author']
    search_fields = ['text', 'author__username', 'blog__title']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ActionLogInline]
    
    def preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    
    preview.short_description = 'Коментар'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'location', 'website', 'action_logs_count']
    search_fields = ['user__username', 'bio', 'location']
    readonly_fields = ['social_links_display']
    fieldsets = (
        ('Основна інформація', {'fields': ('user', 'bio', 'avatar')}),
        ('Контакти', {'fields': ('website', 'location', 'birth_date')}),
        ('Соціальні мережі', {'fields': ('social_links_display',), 'classes': ('collapse',)}),
    )
    inlines = [ActionLogInline]
    
    def social_links_display(self, obj):
        if not obj.social_links:
            return "Немає посилань"
        html = []
        for platform, url in obj.social_links.items():
            html.append(f'<div><strong>{platform}:</strong> <a href="{url}" target="_blank">{url}</a></div>')
        return format_html(''.join(html))
    
    social_links_display.short_description = 'Соціальні мережі'
    
    def action_logs_count(self, obj):
        return obj.action_logs.count()
    
    action_logs_count.short_description = 'Логи'