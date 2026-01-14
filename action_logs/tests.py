# action_logs/tests.py
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import ActionLog, Blog, Comment, UserProfile


class ActionLogModelTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.blog = Blog.objects.create(
            title='Test Blog',
            content='Test content',
            author=self.user
        )
    
    def test_action_log_creation(self):
        log = ActionLog.objects.create(
            action_type='create',
            user=self.user,
            content_object=self.blog,
            description='Test log creation'
        )
        
        self.assertEqual(log.action_type, 'create')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.content_object, self.blog)
        self.assertIsNotNone(log.timestamp)
        self.assertEqual(log.description, 'Test log creation')
    
    def test_generic_foreign_key(self):
        log = ActionLog.objects.create(
            action_type='update',
            user=self.user,
            content_object=self.blog
        )
        
        content_type = ContentType.objects.get_for_model(Blog)
        self.assertEqual(log.content_type, content_type)
        self.assertEqual(str(log.object_id), str(self.blog.id))
        
        self.assertEqual(log.content_object, self.blog)
    
    def test_action_log_str(self):
        log = ActionLog.objects.create(
            action_type='delete',
            user=self.user,
            content_object=self.blog
        )
        
        str_representation = str(log)
        self.assertIn('Видалення', str_representation)
        self.assertIn('testuser', str_representation)
        self.assertIn('Test Blog', str_representation)
    
    def test_log_action_method(self):
        log = ActionLog.log_action(
            user=self.user,
            action_type='view',
            obj=self.blog,
            description='User viewed blog',
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(log.action_type, 'view')
        self.assertEqual(log.description, 'User viewed blog')
        self.assertEqual(log.ip_address, '127.0.0.1')
    
    def test_action_logs_relation(self):
        ActionLog.objects.create(
            action_type='create',
            user=self.user,
            content_object=self.blog,
            description='First log'
        )
        
        ActionLog.objects.create(
            action_type='update',
            user=self.user,
            content_object=self.blog,
            description='Second log'
        )
        
        logs = self.blog.action_logs.all()
        self.assertEqual(logs.count(), 2)
        
        logs_via_method = self.blog.get_action_logs()
        self.assertEqual(logs_via_method.count(), 2)
    
    def test_logged_model_inheritance(self):
        comment = Comment.objects.create(
            blog=self.blog,
            author=self.user,
            text='Test comment'
        )
        
        self.assertTrue(hasattr(comment, 'action_logs'))
        
        comment.log_action(
            user=self.user,
            action_type='create',
            description='Comment created'
        )
        
        logs = comment.get_action_logs()
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().description, 'Comment created')
    
    def test_content_type_filtering(self):
        profile = UserProfile.objects.create(user=self.user)

        ActionLog.objects.create(
            action_type='create',
            user=self.user,
            content_object=self.blog
        )
        
        ActionLog.objects.create(
            action_type='update',
            user=self.user,
            content_object=profile
        )
        blog_content_type = ContentType.objects.get_for_model(Blog)
        blog_logs = ActionLog.objects.filter(content_type=blog_content_type)
        
        self.assertEqual(blog_logs.count(), 1)
        self.assertEqual(blog_logs.first().content_object, self.blog)
    
    def test_action_log_properties(self):
        log = ActionLog.objects.create(
            action_type='create',
            user=self.user,
            content_object=self.blog
        )
        
        self.assertEqual(log.object_type, 'Blog')
        
        log2 = ActionLog.objects.create(
            action_type='login',
            user=self.user,
            description='User login'
        )
        
        self.assertEqual(log2.object_type, 'Немає')


class ActionLogAdminTest(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@example.com'
        )
        
        self.client.login(username='admin', password='admin123')
    
    def test_admin_access(self):
        response = self.client.get('/admin/action_logs/actionlog/')
        self.assertEqual(response.status_code, 200)
    
    def test_admin_list_display(self):
        response = self.client.get('/admin/action_logs/actionlog/')
        self.assertContains(response, 'Дія')
        self.assertContains(response, 'Користувач')
        self.assertContains(response, 'Об\'єкт')


class SignalTest(TestCase):
    
    def test_user_save_signal(self):
        user_count_before = ActionLog.objects.count()
        
        user = User.objects.create_user(
            username='signal_test',
            password='testpass'
        )
        
        user_count_after = ActionLog.objects.count()
        
        self.assertEqual(user_count_after, user_count_before + 1)
        
        log = ActionLog.objects.filter(user=user).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action_type, 'create')
    
    def test_blog_delete_signal(self):
        user = User.objects.create_user(username='bloguser', password='testpass')
        blog = Blog.objects.create(
            title='Signal Test Blog',
            content='Content',
            author=user
        )
        
        blog_id = blog.id
        blog.delete()
        
        log = ActionLog.objects.filter(
            description__contains='Signal Test Blog'
        ).first()
        
        self.assertIsNotNone(log)
        self.assertEqual(log.action_type, 'delete')
