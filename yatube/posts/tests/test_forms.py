import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User')
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test-group',
            description='Тестовое описание группы'
        )
        cls.other_group = Group.objects.create(
            title='Тестовый другой заголовок',
            description='Тестовое другое описание',
            slug='test-other_slug'
        )
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
            content_type='image/gif',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст поста',
            author=cls.user,
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий'
        )
        cls.form = PostForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    @override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
    def test_post_create_post(self):
        """Проверка создания нового поста авторизованным клиентом"""
        post_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'files': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        last_post = Post.objects.order_by('-id').first()
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user}))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group.id, form_data['group'])
        self.assertEqual(form_data['files'].name, self.uploaded.name)

    def test_create_post_guest_client(self):
        """Попытка создать запись как аноним"""
        posts_count = Post.objects.count()
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'files': self.uploaded,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        post_create_url = reverse('posts:post_create')
        login_create_post = reverse('users:login')
        post_create_redirect = f'{login_create_post}?next={post_create_url}'
        self.assertRedirects(response, post_create_redirect)
        self.assertEqual(Post.objects.count(), posts_count)

    def edit_tests(self, response, form_data, id):
        """Повторяющиеся тесты для проверки редактирования"""
        post_upd = Post.objects.get(id=self.post.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(post_upd.text, form_data['text'])
        self.assertNotEqual(post_upd.group.id, form_data['group'])

    def test_edit_post(self):
        """Проверка редактирования поста автором"""
        form_data = {
            'text': 'Измененный текст поста',
            'group': self.other_group.id,
            'files': self.uploaded
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=[self.post.id]
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=[self.post.id]
            )
        )
        post_upd = Post.objects.get(id=self.post.id)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(post_upd.text, form_data['text'])
        self.assertEqual(post_upd.group.id, form_data['group'])

    def test_edit_post_guest_client(self):
        """Проверка редактирования поста
        не авторизованным клиентом"""
        form_data = {
            'text': 'Измененный текст поcта',
            'group': self.other_group.id,
            'files': self.uploaded
        }
        response = self.client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            ),
            data=form_data,
            follow=True
        )
        post_edit_url = reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}
        )
        login_create_post = reverse('users:login')
        post_edit_redirect = f'{login_create_post}?next={post_edit_url}'
        self.assertRedirects(response, post_edit_redirect)
        self.edit_tests(response, form_data, self.post.id)

    def test_no_author_edit_post(self):
        """Проверка редактирования поста не автором"""
        self.user = User.objects.create_user(username='User2')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        form_data = {
            'text': 'Измененный текст поста',
            'group': self.other_group.id,
            'files': self.uploaded
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=[self.post.id],
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id})
        )
        self.edit_tests(response, form_data, self.post.id)

    def test_text_label(self):
        """Проверка label создания поста"""
        text_label = PostFormTests.form.fields['text'].label
        self.assertEqual(text_label, 'Текст поста')

    def test_group_label(self):
        """Проверка label для выбора сообщества поста"""
        group_label = PostFormTests.form.fields['group'].label
        self.assertEqual(group_label, 'Выберите сообщество для поста')

    def test_create_comment(self):
        """Авторизованный юзер может создать комментарий к посту."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': self.comment.text,
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        last_object = Comment.objects.order_by("-id").first()
        self.assertEqual(form_data['text'], last_object.text)

    def test_create_comment_guest_client(self):
        """Проверка невозможности создания комментария гостем"""
        comment_count = Comment.objects.count()
        form_data = {
            'text': self.comment.text,
            'author': self.comment.author,
        }
        response = self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        login_create_post = reverse('users:login')
        post_create_url = reverse(
            'posts:add_comment', kwargs={'post_id': self.post.id})
        comment_create_redirect = f'{login_create_post}?next={post_create_url}'
        self.assertRedirects(response, comment_create_redirect)
        self.assertEqual(Comment.objects.count(), comment_count)
