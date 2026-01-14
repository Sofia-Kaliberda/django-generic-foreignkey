from django.views.generic import DetailView, CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import ActionLog, Blog, Comment, UserProfile
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User


class ActionLogDetailView(LoginRequiredMixin, DetailView):
    model = ActionLog
    template_name = 'action_logs/log_detail.html'
    context_object_name = 'log'

    def get_object(self):
        return get_object_or_404(ActionLog, id=self.kwargs['pk'])


class ActionLogListView(LoginRequiredMixin, ListView):
    model = ActionLog
    template_name = 'action_logs/log_list.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.GET.get('user_id')
        action_type = self.request.GET.get('action_type')

        if user_id:
            queryset = queryset.filter(user__id=user_id)
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_types'] = ActionLog.ACTION_TYPES
        context['users'] = User.objects.all()[:10]
        return context


class BlogListView(ListView):
    model = Blog
    template_name = 'action_logs/blog_list.html'
    context_object_name = 'blogs'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_published=True)
        return queryset


class BlogDetailView(DetailView):
    model = Blog
    template_name = 'action_logs/blog_detail.html'
    context_object_name = 'blog'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blog = self.get_object()
        context['comments'] = blog.comments.filter(is_active=True)
        return context


class BlogCreateView(LoginRequiredMixin, CreateView):
    model = Blog
    template_name = 'action_logs/blog_form.html'
    fields = ['title', 'content', 'is_published', 'tags']
    success_url = reverse_lazy('blog_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class BlogUpdateView(LoginRequiredMixin, UpdateView):
    model = Blog
    template_name = 'action_logs/blog_form.html'
    fields = ['title', 'content', 'is_published', 'tags']
    success_url = reverse_lazy('blog_list')

    def dispatch(self, request, *args, **kwargs):
        blog = self.get_object()
        if blog.author != request.user:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class BlogDeleteView(LoginRequiredMixin, DeleteView):
    model = Blog
    template_name = 'action_logs/blog_confirm_delete.html'
    success_url = reverse_lazy('blog_list')

    def dispatch(self, request, *args, **kwargs):
        blog = self.get_object()
        if blog.author != request.user:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    template_name = 'action_logs/comment_form.html'
    fields = ['text']

    def get_success_url(self):
        return reverse_lazy('blog_detail', kwargs={'pk': self.object.blog.pk})

    def form_valid(self, form):
        blog = get_object_or_404(Blog, pk=self.kwargs['blog_pk'])
        form.instance.author = self.request.user
        form.instance.blog = blog
        return super().form_valid(form)


class ObjectLogListView(LoginRequiredMixin, ListView):
    template_name = 'action_logs/object_logs.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        content_type_id = self.kwargs['content_type_id']
        object_id = self.kwargs['object_id']

        return ActionLog.objects.filter(
            content_type_id=content_type_id,
            object_id=object_id
        ).select_related('user', 'content_type')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get(id=self.kwargs['content_type_id'])
        try:
            obj = content_type.get_object_for_this_type(id=self.kwargs['object_id'])
            context['object'] = obj
        except:
            context['object'] = None
        return context


class DashboardView(LoginRequiredMixin, ListView):
    template_name = 'action_logs/dashboard.html'

    def get_queryset(self):
        return ActionLog.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['recent_logs'] = ActionLog.objects.all()[:10]
        context['user_blogs'] = Blog.objects.filter(author=user)[:5]
        context['user_comments'] = Comment.objects.filter(author=user)[:5]
        context['activity_count'] = ActionLog.objects.filter(user=user).count()

        return context