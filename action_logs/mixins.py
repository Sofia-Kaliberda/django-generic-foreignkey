from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class OwnerRequiredMixin:
    owner_field = 'author'
    permission_denies_message = 'You do not have rights for this action'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if getattr(self.object, self.owner_field) != request.user:
            return HttpResponseForbidden(self.permission_denies_message)
        
        return super().dispatch(request, *args, **kwargs)
    

class AutoAuthorMixin:
    author_field = 'author'

    def form_valid(self, form):
        form.instance = self.set_author(form.instance)
        return super().form.valid(form)
    
    def set_author(self,instance):
        setattr(instance, self.author_field, self.request.user)
        return instance

class QueryFilterMixin:
    filter_fields = []
    search_fields = []
    date_range_field = None
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        for field in self.filter_fields:
            value = self.request.GET.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        
        search_query = self.request.GET.get('search')
        if search_query and self.search_fields:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f'{field}__icontains': search_query})
            queryset = queryset.filter(q_objects)
        
        if self.date_range_field:
            start_date = self.request.GET.get('start_date')
            end_date = self.request.GET.get('end_date')
            if start_date:
                queryset = queryset.filter(**{f'{self.date_range_field}__gte': start_date})
            if end_date:
                queryset = queryset.filter(**{f'{self.date_range_field}__lte': end_date})
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_params'] = self.request.GET.dict()
        return context

class JSONResponseMixin:
    json_fields = []
    include_model_name = False
    
    def render_to_json_response(self, context, **response_kwargs):
        data = self.serialize_context(context)
        return JsonResponse(data, **response_kwargs)
    
    def serialize_context(self, context):
        if self.json_fields:
            data = {}
            for field in self.json_fields:
                if field in context:
                    data[field] = self.serialize_value(context[field])
        else:
            object_name = getattr(self, 'context_object_name', None)
            if object_name and object_name in context:
                data = self.serialize_object(context[object_name])
            else:
                data = context
        
        if self.include_model_name and hasattr(self, 'model'):
            data['model'] = self.model.__name__
        
        return data
    
    def serialize_value(self, value):
        if hasattr(value, '__dict__'):
            return str(value)
        elif hasattr(value, 'all'):
            return list(value.values())
        return value
    
    def serialize_object(self, obj):
        if hasattr(obj, 'values'):
            return list(obj.values())
        elif hasattr(obj, '__dict__'):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        return obj
    
class CacheViewMixin:
    cache_timeout = 60 * 5
    cache_key_prefix = 'view_cache'
    vary_on_user = False
    
    def get_cache_key(self):
        base_key = f"{self.cache_key_prefix}:{self.request.path}"
        if self.vary_on_user and self.request.user.is_authenticated:
            base_key += f":user_{self.request.user.id}"
        
        query_params = self.request.GET.urlencode()
        if query_params:
            base_key += f":{hash(query_params)}"
        
        return base_key
    
    def get(self, request, *args, **kwargs):
        cache_key = self.get_cache_key()
        cached_response = cache.get(cache_key)
        
        if cached_response is not None:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_response
        
        logger.debug(f"Cache miss for {cache_key}")
        response = super().get(request, *args, **kwargs)
        
        if response.status_code == 200:
            cache.set(cache_key, response, self.cache_timeout)
        
        return response


class ActionLoggingMixin:
    log_action = True
    action_type = 'view'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        if self.log_action and request.user.is_authenticated:
            self.log_user_action(request, response, *args, **kwargs)
        
        return response
    
    def log_user_action(self, request, response, *args, **kwargs):
        from .models import ActionLog
        
        try:
            obj = None
            if hasattr(self, 'object'):
                obj = self.object
            elif hasattr(self, 'get_object'):
                try:
                    obj = self.get_object()
                except:
                    pass
            
            ActionLog.objects.create(
                user=request.user,
                action_type=self.action_type,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                object_id=obj.id if obj else None,
                content_type=obj.__class__ if obj else None,
                additional_data=self.get_log_data(request, response, *args, **kwargs)
            )
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_log_data(self, request, response, *args, **kwargs):
        return {
            'view_class': self.__class__.__name__,
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
        }


class PublicPrivateMixin:
    public_field = 'is_published'
    show_all_to_staff = True
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(**{self.public_field: True})
        elif self.show_all_to_staff and self.request.user.is_staff:
            pass
        else:
            queryset = queryset.filter(
                Q(**{self.public_field: True}) | 
                Q(**{self.get_owner_lookup()})
            )
        
        return queryset
    
    def get_owner_lookup(self):
        owner_field = getattr(self, 'owner_field', 'author')
        return {owner_field: self.request.user}


class EnhancedPaginationMixin:
    paginate_by = 10
    page_kwarg = 'page'
    allow_all = False
    max_per_page = 100
    
    def get_paginate_by(self, queryset):
        if self.allow_all and self.request.GET.get('show') == 'all':
            return None
        
        per_page = self.request.GET.get('per_page', self.paginate_by)
        try:
            per_page = int(per_page)
            if per_page > self.max_per_page:
                per_page = self.max_per_page
            return per_page
        except (ValueError, TypeError):
            return self.paginate_by
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context.get('page_obj')
        
        if page_obj:
            paginator = page_obj.paginator
            context['pagination_info'] = {
                'total_items': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'has_previous': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'per_page': paginator.per_page,
            }
        
        return context


class RelatedObjectsMixin:
    related_objects = {}
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object() if hasattr(self, 'get_object') else None
        
        if obj:
            for name, relation in self.related_objects.items():
                if callable(relation):
                    context[name] = relation(obj)
                else:
                    context[name] = getattr(obj, relation).all()
        
        return context

class ObjectLogsMixin:
    
    logs_limit = 10
    include_logs = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.include_logs and hasattr(self, 'get_object'):
            try:
                obj = self.get_object()
                if obj and hasattr(obj, 'id'):
                    from django.contrib.contenttypes.models import ContentType
                    from .models import ActionLog
                    
                    content_type = ContentType.objects.get_for_model(obj)
                    context['object_logs'] = ActionLog.objects.filter(
                        content_type=content_type,
                        object_id=obj.id
                    ).select_related('user')[:self.logs_limit]
            except:
                context['object_logs'] = []
        
        return context
