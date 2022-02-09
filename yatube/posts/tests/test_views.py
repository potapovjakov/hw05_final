import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.user = User.objects.create_user(username='User')
        cls.user_2 = User.objects.create_user(username='User2')
        cls.authorized_client = Client()
        cls.authorized_client_2 = Client()
        cls.post = Post.objects.create(
            author=cls.user,
            text='Text for TEST',
            group=cls.group,
            image=cls.uploaded,
        )
        cls.other_group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-other_slug'
        )
        cls.follow_index = reverse('posts:follow_index')

    def setUp(self):
        self.authorized_client_2.force_login(self.user_2)
        self.authorized_client.force_login(self.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """URL-адрес(view функция) использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:posts_group', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}):
                'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_context(self, response):
        first_object = response.context['page_obj'].object_list[0]
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author.username, self.user.username)
        self.assertEqual(first_object.group.title, self.group.title)
        self.assertEqual(first_object.id, self.post.id)
        self.assertEqual(first_object.image, self.post.image)

    def test_post_index_page_show_correct_context(self):
        """Проверяем контекст страницы index"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.check_context(response)

    def test_post_posts_groups_page_show_correct_context(self):
        """Проверяем контекст страницы posts_groups"""
        response = self.authorized_client.get(
            reverse('posts:posts_group', kwargs={'slug': self.group.slug}))
        self.check_context(response)

    def test_post_profile_page_show_correct_context(self):
        """Проверяем контекст страницы profile"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user}))
        self.check_context(response)

    def test_post_post_detail_page_show_correct_context(self):
        """Проверяем контекст страницы post_detail"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id})).context['post']
        self.assertEqual(response.pk, self.post.pk)
        self.assertEqual(response.image, self.post.image)

    def test_post_posts_edit_page_show_correct_context(self):
        """Проверяем контекст страницы post_edit"""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.pk})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_post_create_page_show_correct_context(self):
        """Проверяем контекст страницы post_create"""
        response = self.authorized_client.get(
            reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_new_create(self):
        """Проверяем, что при создании поста:
        пост появляется на главной странице,
        на странице выбранной группы,
        в профайле пользователя"""
        new_post = Post.objects.create(
            author=self.user,
            text='Post text for TEST',
            group=self.group
        )
        exp_pages = [
            reverse('posts:index'),
            reverse(
                'posts:posts_group', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': self.user})
        ]
        for rev in exp_pages:
            with self.subTest(rev=rev):
                response = self.authorized_client.get(rev)
                self.assertIn(
                    new_post, response.context['page_obj']
                )

    def test_post_new_not_in_group(self):
        """Проверяем, что созданный пост не попал в другую группу,
        для которой не был предназначен."""
        new_post = Post.objects.create(
            author=self.user,
            text='Post text for TEST',
            group=self.group,
        )
        response = self.authorized_client.get(
            reverse(
                'posts:posts_group',
                kwargs={'slug': self.other_group.slug}),
        )
        self.assertNotIn(new_post, response.context['page_obj'])

    def test_follow_for_auth(self):
        """Проверяем функцию profile_follow"""
        self.authorized_client.post(reverse(
            'posts:profile_follow', kwargs={'username': self.user_2})
        )
        self.assertIs(
            Follow.objects.filter(
                user=self.user).filter(
                author=self.user_2).exists(),
            True
        )

    def test_unfollow_for_auth(self):
        """Проверяем функцию profile_unfollow"""
        self.authorized_client.post(reverse(
            'posts:profile_follow', kwargs={'username': self.user_2})
        )
        self.authorized_client.post(reverse(
            'posts:profile_unfollow', kwargs={'username': self.user_2}))
        self.assertIs(
            Follow.objects.filter(
                user=self.user).filter(
                author=self.user_2).exists(),
            False
        )

    def test_follow_index(self):
        """Проверяем follow index"""
        response_context = self.authorized_client.get(self.follow_index)
        post_context = response_context.context['page_obj']
        self.assertTrue(Post.objects.get(
            text=self.post.text),
            post_context
        )
        response_2 = self.authorized_client_2.get(self.follow_index)
        post_2 = response_2.context['page_obj']
        self.assertNotEqual(
            post_2,
            Post.objects.get(text=self.post.text)
        )

    def test_cache_index(self):
        """Проверка кеширования главной страницы index."""
        response1 = self.authorized_client.get(reverse("posts:index"))
        Post.objects.create(
            author=self.user,
            text=self.post.text,
        )
        response2 = self.authorized_client.get(reverse("posts:index"))
        self.assertEqual(response1.content, response2.content)
        cache.clear()
        response3 = self.authorized_client.get(reverse("posts:index"))
        self.assertNotEqual(response1.content, response3.content)
