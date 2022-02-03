from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.user = User.objects.create_user(username='NoName')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client(self.user)
        self.authorized_client.force_login(self.user)

    def test_404_page(self):
        """Проверка запроса к несуществующей странице"""
        page_404 = '/unexisting_page/'
        response = self.client.get(page_404)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls(self):
        """Проверка работы страниц"""
        urls = {
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{self.post.id}/',
            '/create/',
            f'/posts/{self.post.id}/edit/',
        }
        for adress in urls:
            with self.subTest(adress=adress):
                response = self.authorized_client.get(
                    adress, follow=True
                )
                self.assertEqual(response.status_code, HTTPStatus.OK.value)

    def test_urls_guest(self):
        """Проверка работы страниц для  неавторизованного пользователя"""
        urls = {
            '/': HTTPStatus.OK.value,
            f'/group/{self.group.slug}/': HTTPStatus.OK.value,
            f'/profile/{self.user.username}/': HTTPStatus.OK.value,
            f'/posts/{self.post.id}/': HTTPStatus.OK.value,
            '/create/': HTTPStatus.FOUND,
            f'/posts/{self.post.id}/edit/': HTTPStatus.FOUND,
        }
        for adress, expected in urls.items():
            with self.subTest(adress=adress):
                response = self.client.get(
                    adress
                )
                self.assertEqual(response.status_code, expected)

    def test_redirect_if_not_logged_in(self):
        """URL-адрес '/create/' использует перенаправление,
        для неавторизованного пользователя"""
        response = self.client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(response, '/auth/login/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон,
        для неавторизованного пользователя"""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user}/': 'posts/profile.html',
            f'/posts/{self.post.author.pk}/': 'posts/post_detail.html',
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_home_url_uses_correct_template(self):
        """Страница по адресу '/create/' использует шаблон 'posts/create_post.html'
         для авторизованного пользователя"""
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_edit_page_correct_template(self):
        '''URL '/edit/' редактирования поста использует шаблон create.html
        для автора поста'''
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.author.pk})
        )
        self.assertTemplateUsed(response, 'posts/create_post.html')
