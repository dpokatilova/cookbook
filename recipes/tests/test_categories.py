import pytest
from recipes.models import Category


@pytest.mark.django_db
def test_get_categories_empty(api_client):
    response = api_client.get("/categories/")
    assert response.status_code == 200
    assert response.data == []


@pytest.mark.django_db
def test_get_categories_list(api_client, category):
    response = api_client.get("/categories/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["name"] == "Сніданки"


@pytest.mark.django_db
def test_get_category_not_found(api_client):
    response = api_client.get("/categories/9999/")
    assert response.status_code == 404
    assert "error" in response.data


@pytest.mark.django_db
def test_create_category_anonymous_unauthorized(api_client):
    response = api_client.post("/categories/", {"name": "Десерти"}, format="json")
    assert response.status_code == 401
    assert not Category.objects.filter(name="Десерти").exists()


@pytest.mark.django_db
def test_create_category_user_forbidden(user_client):
    response = user_client.post("/categories/", {"name": "Десерти"}, format="json")
    assert response.status_code == 403
    assert "адміністратори" in response.data["detail"]


@pytest.mark.django_db
def test_create_category_admin_success(admin_client):
    response = admin_client.post("/categories/", {"name": "Десерти"}, format="json")
    assert response.status_code == 201
    assert response.data["name"] == "Десерти"
    assert Category.objects.filter(name="Десерти").exists()


@pytest.mark.django_db
def test_delete_category_with_recipes_conflict(admin_client, category, recipe):
    response = admin_client.delete(f"/categories/{category.id}/")
    assert response.status_code == 409
    assert Category.objects.filter(id=category.id).exists()


@pytest.mark.django_db
def test_search_categories(api_client, category):
    Category.objects.create(name="Обіди")
    response = api_client.get("/categories/?search=Сні")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["name"] == "Сніданки"


@pytest.mark.django_db
def test_get_category_detail(api_client, category):
    response = api_client.get(f"/categories/{category.id}/")
    assert response.status_code == 200
    assert response.data == {"id": category.id, "name": "Сніданки"}


@pytest.mark.django_db
def test_create_category_empty_name(admin_client):
    response = admin_client.post("/categories/", {"name": ""}, format="json")
    assert response.status_code == 400
    assert "name" in response.data["details"]


@pytest.mark.django_db
def test_create_category_duplicate_name(admin_client, category):
    response = admin_client.post("/categories/", {"name": "Сніданки"}, format="json")
    assert response.status_code == 400
    assert "name" in response.data["details"]
    assert Category.objects.filter(name="Сніданки").count() == 1


@pytest.mark.django_db
def test_create_category_invalid_token(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid")
    response = api_client.post("/categories/", {"name": "Десерти"}, format="json")
    assert response.status_code == 401
    assert not Category.objects.filter(name="Десерти").exists()


@pytest.mark.django_db
def test_update_category_admin_success(admin_client, category):
    response = admin_client.put(
        f"/categories/{category.id}/", {"name": "Сніданки та бранчі"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["name"] == "Сніданки та бранчі"
    category.refresh_from_db()
    assert category.name == "Сніданки та бранчі"


@pytest.mark.django_db
def test_update_category_user_forbidden(user_client, category):
    response = user_client.put(
        f"/categories/{category.id}/", {"name": "Інша назва"}, format="json"
    )
    assert response.status_code == 403
    category.refresh_from_db()
    assert category.name == "Сніданки"


@pytest.mark.django_db
def test_update_category_not_found(admin_client):
    response = admin_client.put("/categories/9999/", {"name": "Нова"}, format="json")
    assert response.status_code == 404
    assert "error" in response.data


@pytest.mark.django_db
def test_delete_category_admin_success(admin_client, category):
    response = admin_client.delete(f"/categories/{category.id}/")
    assert response.status_code == 204
    assert not Category.objects.filter(id=category.id).exists()


@pytest.mark.django_db
def test_delete_category_anonymous_unauthorized(api_client, category):
    response = api_client.delete(f"/categories/{category.id}/")
    assert response.status_code == 401
    assert Category.objects.filter(id=category.id).exists()


@pytest.mark.django_db
def test_delete_category_not_found(admin_client):
    response = admin_client.delete("/categories/9999/")
    assert response.status_code == 404
    assert "error" in response.data


@pytest.mark.django_db
def test_update_category_empty_name(admin_client, category):
    response = admin_client.put(
        f"/categories/{category.id}/", {"name": ""}, format="json"
    )
    assert response.status_code == 400
    assert "name" in response.data["details"]
