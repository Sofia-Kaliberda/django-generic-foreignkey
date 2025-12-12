import random
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from action_logs.models import ActionLog, Blog, Comment, UserProfile


class Command(BaseCommand):
    help = 'Створення тестових даних для ActionLog'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Кількість тестових користувачів'
        )
        parser.add_argument(
            '--blogs',
            type=int,
            default=10,
            help='Кількість тестових блогів'
        )
        parser.add_argument(
            '--comments',
            type=int,
            default=20,
            help='Кількість тестових коментарів'
        )
        parser.add_argument(
            '--logs',
            type=int,
            default=30,
            help='Кількість додаткових логів'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Початок створення тестових даних...'))

        ActionLog.objects.all().delete()
        Comment.objects.all().delete()
        Blog.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.exclude(is_superuser=True).delete()
        
        users = []
        for i in range(options['users']):
            user = User.objects.create_user(
                username=f'test_user_{i+1}',
                email=f'user{i+1}@example.com',
                password='testpass123',
                first_name=f'Ім\'я_{i+1}',
                last_name=f'Прізвище_{i+1}'
            )
            users.append(user)
            
            profile = UserProfile.objects.create(
                user=user,
                bio=f'Біографія користувача {user.username}',
                location=random.choice(['Київ', 'Львів', 'Одеса', 'Харків', 'Дніпро']),
                website=f'https://{user.username}.example.com',
                social_links={
                    'facebook': f'https://facebook.com/{user.username}',
                    'twitter': f'https://twitter.com/{user.username}',
                    'linkedin': f'https://linkedin.com/in/{user.username}'
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Створено {len(users)} користувачів'))

        blogs = []
        for i in range(options['blogs']):
            days_ago = random.randint(0, 30)
            created_at = timezone.now() - timedelta(days=days_ago)
            
            blog = Blog.objects.create (
                title=f'Тестовий блог #{i+1}: {random.choice(["Про програмування", "Про подорожі", "Про кулінарію", "Про спорт"])}',
                content={' '.join([f"Абзац {j+1}." for j in range(random.randint(3, 10))])},
                author=random.choice(users),
                is_published=random.choice([True, False, True]),
                tags=random.sample(['python', 'django', 'web', 'dev', 'travel', 'food', 'sport'], k=3)
            )
            
            Blog.objects.filter(id=blog.id).update(created_at=created_at)
            blog.refresh_from_db()
            blogs.append(blog)
        
        self.stdout.write(self.style.SUCCESS(f'Створено {len(blogs)} блогів'))

        comments = []
        for i in range(options['comments']):
            days_ago = random.randint(0, 15)
            created_at = timezone.now() - timedelta(days=days_ago)
            
            comment = Comment.objects.create(
                blog=random.choice(blogs),
                author=random.choice(users),
                text=f'''
                Це тестовий коментар #{i+1}.
                {' '.join([f"Частина {j+1} коментаря." for j in range(random.randint(1, 5))])}
                ''',
                is_active=random.choice([True, False, True, True])
            )
            
            Comment.objects.filter(id=comment.id).update(created_at=created_at)
            comment.refresh_from_db()
            comments.append(comment)
        
        self.stdout.write(self.style.SUCCESS(f'Створено {len(comments)} коментарів'))
        
        action_types = [choice[0] for choice in ActionLog.ACTION_TYPES]
        descriptions = [
            'Створення нового обʼєкта',
            'Оновлення існуючого обʼєкта',
            'Видалення обʼєкта',
            'Перегляд деталей',
            'Успішний вхід в систему',
            'Вихід з системи',
            'Інша системна дія',
            'Завантаження файлу',
            'Відправка повідомлення',
            'Зміна налаштувань'
        ]
        
        all_objects = list(blogs) + list(comments) + list(users) + list(UserProfile.objects.all())
        
        for i in range(options['logs']):
            content_obj = random.choice(all_objects) if all_objects else None
            
            log_user = random.choice(users + [None, None])

            log = ActionLog.objects.create(
                action_type=random.choice(action_types),
                user=log_user,
                content_object=content_obj,
                description=random.choice(descriptions) + f" (лог #{i+1})",
                ip_address=f'192.168.1.{random.randint(1, 255)}',
                user_agent=random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/537.36'
                ])
            )
            
            days_ago = random.randint(0, 60)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            log_timestamp = timezone.now() - timedelta(
                days=days_ago,
                hours=hours_ago,
                minutes=minutes_ago
            )
            
            ActionLog.objects.filter(id=log.id).update(timestamp=log_timestamp)
        
        self.stdout.write(self.style.SUCCESS(f'Створено {options["logs"]} додаткових логів'))
        
        self.print_statistics()
    
    def print_statistics(self):
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('СТАТИСТИКА СТВОРЕНИХ ДАНИХ:'))
        self.stdout.write('='*50)
        
        stats = [
            ('Користувачі', User.objects.count()),
            ('Профілі', UserProfile.objects.count()),
            ('Блоги', Blog.objects.count()),
            ('Коментарі', Comment.objects.count()),
            ('Логи дій', ActionLog.objects.count()),
        ]
        
        for name, count in stats:
            self.stdout.write(f'{name}: {self.style.SUCCESS(str(count))}')
        
        self.stdout.write('\n' + '-'*50)
        self.stdout.write('ЛОГИ ПО ТИПАХ ДІЙ:')
        self.stdout.write('-'*50)
        
        for action_type, display_name in ActionLog.ACTION_TYPES:
            count = ActionLog.objects.filter(action_type=action_type).count()
            if count > 0:
                self.stdout.write(f'{display_name}: {count}')
        
        self.stdout.write('\n' + '-'*50)
        self.stdout.write('ЛОГИ ПО ТИПАХ ОБ\'ЄКТІВ:')
        self.stdout.write('-'*50)
        
        content_types = ContentType.objects.filter(
            pk__in=ActionLog.objects.values_list('content_type', flat=True).distinct()
        )
        
        for ct in content_types:
            count = ActionLog.objects.filter(content_type=ct).count()
            model_name = ct.model_class().__name__
            self.stdout.write(f'{model_name}: {count}')
        
        self.stdout.write('\n' + '-'*50)
        self.stdout.write('ОСТАННІ 5 ЛОГІВ:')
        self.stdout.write('-'*50)
        
        for log in ActionLog.objects.all().order_by('-timestamp')[:5]:
            user_str = log.user.username if log.user else 'Анонім'
            obj_str = str(log.content_object)[:30] if log.content_object else 'Немає'
            
            self.stdout.write(
                f'{log.timestamp.strftime("%d.%m.%Y %H:%M")} | '
                f'{user_str:15} | '
                f'{log.get_action_type_display():10} | '
                f'{obj_str}'
            )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Тестові дані успішно створені!'))
        self.stdout.write(self.style.WARNING('Суперкористувач: admin / admin123'))