from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.posts = [
            Post.objects.create(
                author=cls.user,
                text='Post text № {i}',
                group=cls.group,
            )
            for i in range(56)
        ]
        cls.urls = [
            reverse("posts:index"),
            reverse("posts:profile", args={cls.user.username}),
            reverse("posts:posts_group", args={cls.group.slug}),
        ]
        cache.clear()

    def setUp(self):
        self.authorized_client = Client(self.user)
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_records(self):
        """Паджинатор выводит на первую страницу столько постов,
        сколько указано в константе NUMPOSTS в settings.py"""
        for reverse_name in self.urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(
                    len(response.context["page_obj"]), settings.NUMPOSTS)

    def test_second_page_contains_records(self):
        """Паджинатор выводит оставшиеся записи на последней странице."""
        response = self.authorized_client.get(reverse('posts:index'))
        per_page = response.context['page_obj'].paginator.per_page
        cnt_pages = response.context['page_obj'].paginator.count
        self.assertEqual(per_page, settings.NUMPOSTS)
        for reverse_name in self.urls:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(
                    reverse_name + '?page=' + str(
                        int(cnt_pages / settings.NUMPOSTS) + 1)
                )
                self.assertEqual(
                    len(response.context['page_obj']),
                    cnt_pages % settings.NUMPOSTS
                )
