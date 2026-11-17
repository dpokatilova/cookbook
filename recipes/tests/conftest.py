import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from recipes.models import Category, Recipe

PASSWORD = "Testpass!2"


def login(client, username):
    response = client.post(
        "/users/login/",
        {"username": username, "password": PASSWORD},
        format="json",
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(
        username="cook", email="cook@example.com", password=PASSWORD
    )


@pytest.fixture
def admin():
    return User.objects.create_user(
        username="chef", email="chef@example.com", password=PASSWORD, is_staff=True
    )


@pytest.fixture
def user_client(user):
    return login(APIClient(), user.username)


@pytest.fixture
def admin_client(admin):
    return login(APIClient(), admin.username)


@pytest.fixture
def category():
    return Category.objects.create(name="Сніданки")


@pytest.fixture
def recipe(category):
    return Recipe.objects.create(
        title="Омлет", time_minutes=15, calories=200, category=category
    )
