import logging

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import Category, Ingredient, Recipe, RecipeIngredient
from recipes.permissions import IsAdminOrReadOnly
from recipes.serializers import (
    CategorySerializer,
    DetailErrorSerializer,
    ErrorSerializer,
    IngredientSerializer,
    RecipeDetailSerializer,
    RecipeIngredientCreateSerializer,
    RecipeListSerializer,
    RecipeSerializer,
)

logger = logging.getLogger(__name__)


def error_response(message, status_code, details=None):
    return Response(
        {"error": message, "details": details or {}},
        status=status_code,
    )


def not_found(message):
    return error_response(message, status.HTTP_404_NOT_FOUND)


def invalid_data(serializer):
    return error_response(
        "Невалідні дані. Деталі по кожному полю — у details.",
        status.HTTP_400_BAD_REQUEST,
        serializer.errors,
    )


def get_or_none(model, pk):
    return model.objects.filter(pk=pk).first()


CATEGORY_TAGS = ["Категорії"]

AUTH_ERRORS = {
    401: OpenApiResponse(
        DetailErrorSerializer,
        description="Немає токена, або він недійсний чи закінчився.",
    ),
    403: OpenApiResponse(
        DetailErrorSerializer,
        description="Користувач авторизований, але не є адміністратором.",
    ),
}

CATEGORY_NOT_FOUND = OpenApiResponse(
    ErrorSerializer, description="Категорію з таким id не знайдено."
)


class CategoryListView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(
        tags=CATEGORY_TAGS,
        summary="Список категорій",
        description="Повертає всі категорії. Доступно всім, авторизація не потрібна.",
        auth=[],
        parameters=[
            OpenApiParameter(
                name="search",
                type=str,
                required=False,
                description="Пошук за частиною назви, наприклад `?search=Сні`.",
            ),
        ],
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request):
        categories = Category.objects.all()
        search = request.query_params.get("search")
        if search:
            categories = categories.filter(name__icontains=search)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=CATEGORY_TAGS,
        summary="Створити категорію",
        description=(
            "Лише для адміністраторів. "
            "Потрібен заголовок `Authorization: Bearer <access_token>`."
        ),
        request=CategorySerializer,
        responses={
            201: CategorySerializer,
            400: OpenApiResponse(
                ErrorSerializer,
                description="Невалідні дані або категорія з такою назвою вже існує.",
            ),
            **AUTH_ERRORS,
        },
        examples=[
            OpenApiExample("Запит", value={"name": "Десерти"}, request_only=True),
            OpenApiExample(
                "Створено",
                value={"id": 3, "name": "Десерти"},
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Назва вже існує",
                value={
                    "error": "Невалідні дані. Деталі по кожному полю — у details.",
                    "details": {"name": ["category with this name already exists."]},
                },
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "Не адміністратор",
                value={
                    "detail": "Змінювати категорії та інгредієнти можуть лише адміністратори."
                },
                response_only=True,
                status_codes=["403"],
            ),
        ],
    )
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Category create rejected: invalid fields=%s", list(serializer.errors)
            )
            return invalid_data(serializer)
        category = serializer.save()
        logger.info(
            "Category created: id=%s name=%s user=%s",
            category.id,
            category.name,
            request.user.username,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    @extend_schema(
        tags=CATEGORY_TAGS,
        summary="Отримати категорію",
        description="Доступно всім. Рецепти категорії — через `GET /recipes/?category={id}`.",
        auth=[],
        responses={200: CategorySerializer, 404: CATEGORY_NOT_FOUND},
    )
    def get(self, request, pk):
        category = get_or_none(Category, pk)
        if category is None:
            return not_found(f"Категорію з id={pk} не знайдено.")
        return Response(CategorySerializer(category).data)

    @extend_schema(
        tags=CATEGORY_TAGS,
        summary="Оновити категорію",
        description="Лише для адміністраторів. Передається вся категорія (PUT).",
        request=CategorySerializer,
        responses={
            200: CategorySerializer,
            400: OpenApiResponse(ErrorSerializer, description="Невалідні дані."),
            404: CATEGORY_NOT_FOUND,
            **AUTH_ERRORS,
        },
        examples=[
            OpenApiExample(
                "Запит", value={"name": "Сніданки та бранчі"}, request_only=True
            ),
        ],
    )
    def put(self, request, pk):
        category = get_or_none(Category, pk)
        if category is None:
            logger.warning("Category update failed: id=%s not found", pk)
            return not_found(f"Категорію з id={pk} не знайдено.")
        serializer = CategorySerializer(category, data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Category update rejected: id=%s invalid fields=%s",
                pk,
                list(serializer.errors),
            )
            return invalid_data(serializer)
        serializer.save()
        logger.info("Category updated: id=%s user=%s", pk, request.user.username)
        return Response(serializer.data)

    @extend_schema(
        tags=CATEGORY_TAGS,
        summary="Видалити категорію",
        description=(
            "Лише для адміністраторів. "
            "Категорію, до якої належать рецепти, видалити не можна (409)."
        ),
        responses={
            204: OpenApiResponse(description="Категорію видалено."),
            404: CATEGORY_NOT_FOUND,
            409: OpenApiResponse(
                ErrorSerializer,
                description="До категорії належать рецепти.",
            ),
            **AUTH_ERRORS,
        },
        examples=[
            OpenApiExample(
                "У категорії є рецепти",
                value={
                    "error": (
                        "Неможливо видалити категорію «Сніданки», бо до неї належить "
                        "рецептів: 2. Спочатку видаліть ці рецепти або перенесіть "
                        "їх в іншу категорію."
                    ),
                    "details": {},
                },
                response_only=True,
                status_codes=["409"],
            ),
        ],
    )
    def delete(self, request, pk):
        category = get_or_none(Category, pk)
        if category is None:
            logger.warning("Category delete failed: id=%s not found", pk)
            return not_found(f"Категорію з id={pk} не знайдено.")
        recipes_count = category.recipes.count()
        if recipes_count:
            logger.warning(
                "Category delete rejected: id=%s has %s recipes", pk, recipes_count
            )
            return error_response(
                f"Неможливо видалити категорію «{category.name}», "
                f"бо до неї належить рецептів: {recipes_count}. "
                "Спочатку видаліть ці рецепти або перенесіть їх в іншу категорію.",
                status.HTTP_409_CONFLICT,
            )
        category.delete()
        logger.info("Category deleted: id=%s user=%s", pk, request.user.username)
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientListView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        ingredients = Ingredient.objects.all()
        search = request.query_params.get("search")
        if search:
            ingredients = ingredients.filter(name__icontains=search)
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = IngredientSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Ingredient create rejected: invalid fields=%s", list(serializer.errors)
            )
            return invalid_data(serializer)
        ingredient = serializer.save()
        logger.info(
            "Ingredient created: id=%s name=%s user=%s",
            ingredient.id,
            ingredient.name,
            request.user.username,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IngredientDetailView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, pk):
        ingredient = get_or_none(Ingredient, pk)
        if ingredient is None:
            return not_found(f"Інгредієнт з id={pk} не знайдено.")
        return Response(IngredientSerializer(ingredient).data)

    def put(self, request, pk):
        ingredient = get_or_none(Ingredient, pk)
        if ingredient is None:
            logger.warning("Ingredient update failed: id=%s not found", pk)
            return not_found(f"Інгредієнт з id={pk} не знайдено.")
        serializer = IngredientSerializer(ingredient, data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Ingredient update rejected: id=%s invalid fields=%s",
                pk,
                list(serializer.errors),
            )
            return invalid_data(serializer)
        serializer.save()
        logger.info("Ingredient updated: id=%s user=%s", pk, request.user.username)
        return Response(serializer.data)

    def delete(self, request, pk):
        ingredient = get_or_none(Ingredient, pk)
        if ingredient is None:
            logger.warning("Ingredient delete failed: id=%s not found", pk)
            return not_found(f"Інгредієнт з id={pk} не знайдено.")
        recipes_count = ingredient.recipe_ingredients.count()
        if recipes_count:
            logger.warning(
                "Ingredient delete rejected: id=%s used in %s recipes",
                pk,
                recipes_count,
            )
            return error_response(
                f"Неможливо видалити інгредієнт «{ingredient.name}», "
                f"бо він використовується в рецептах: {recipes_count}. "
                "Спочатку приберіть його з цих рецептів.",
                status.HTTP_409_CONFLICT,
            )
        ingredient.delete()
        logger.info("Ingredient deleted: id=%s user=%s", pk, request.user.username)
        return Response(status=status.HTTP_204_NO_CONTENT)


RECIPE_ORDERING = ["time_minutes", "-time_minutes", "calories", "-calories"]


class RecipeListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        recipes = Recipe.objects.all()
        params = request.query_params
        logger.debug("Recipe list requested: params=%s", dict(params))

        for name in ("category", "ingredient", "max_time"):
            value = params.get(name)
            if value and not value.isdigit():
                logger.warning("Recipe list rejected: invalid %s=%s", name, value)
                return error_response(
                    f"Параметр {name} має бути цілим додатним числом.",
                    status.HTTP_400_BAD_REQUEST,
                )

        search = params.get("search")
        if search:
            recipes = recipes.filter(title__icontains=search)
        if params.get("category"):
            recipes = recipes.filter(category_id=params["category"])
        if params.get("ingredient"):
            recipes = recipes.filter(ingredients__id=params["ingredient"])
        if params.get("max_time"):
            recipes = recipes.filter(time_minutes__lte=params["max_time"])

        ordering = params.get("ordering")
        if ordering:
            if ordering not in RECIPE_ORDERING:
                logger.warning("Recipe list rejected: invalid ordering=%s", ordering)
                return error_response(
                    f"Неможливо сортувати за «{ordering}». "
                    f"Доступні варіанти: {', '.join(RECIPE_ORDERING)}.",
                    status.HTTP_400_BAD_REQUEST,
                )
            recipes = recipes.order_by(ordering)

        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RecipeSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Recipe create rejected: invalid fields=%s", list(serializer.errors)
            )
            return invalid_data(serializer)
        recipe = serializer.save()
        logger.info(
            "Recipe created: id=%s title=%s user=%s",
            recipe.id,
            recipe.title,
            request.user.username,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecipeDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            return not_found(f"Рецепт з id={pk} не знайдено.")
        return Response(RecipeDetailSerializer(recipe).data)

    def put(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            logger.warning("Recipe update failed: id=%s not found", pk)
            return not_found(f"Рецепт з id={pk} не знайдено.")
        serializer = RecipeSerializer(recipe, data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Recipe update rejected: id=%s invalid fields=%s",
                pk,
                list(serializer.errors),
            )
            return invalid_data(serializer)
        serializer.save()
        logger.info("Recipe updated: id=%s user=%s", pk, request.user.username)
        return Response(serializer.data)

    def delete(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            logger.warning("Recipe delete failed: id=%s not found", pk)
            return not_found(f"Рецепт з id={pk} не знайдено.")
        recipe.delete()
        logger.info("Recipe deleted: id=%s user=%s", pk, request.user.username)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeIngredientListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            logger.warning("Add ingredient failed: recipe id=%s not found", pk)
            return not_found(f"Рецепт з id={pk} не знайдено.")
        serializer = RecipeIngredientCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Add ingredient rejected: recipe id=%s invalid fields=%s",
                pk,
                list(serializer.errors),
            )
            return invalid_data(serializer)
        ingredient = serializer.validated_data["ingredient"]
        if recipe.recipe_ingredients.filter(ingredient=ingredient).exists():
            logger.warning(
                "Add ingredient rejected: ingredient id=%s already in recipe id=%s",
                ingredient.id,
                pk,
            )
            return error_response(
                f"Інгредієнт «{ingredient.name}» уже є в рецепті "
                f"«{recipe.title}». Щоб змінити кількість, видаліть його "
                "і додайте знову.",
                status.HTTP_409_CONFLICT,
            )
        serializer.save(recipe=recipe)
        logger.info(
            "Ingredient id=%s added to recipe id=%s user=%s",
            ingredient.id,
            pk,
            request.user.username,
        )
        return Response(
            RecipeDetailSerializer(recipe).data,
            status=status.HTTP_201_CREATED,
        )


class RecipeIngredientDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def delete(self, request, pk, ingredient_pk):
        link = RecipeIngredient.objects.filter(
            recipe_id=pk, ingredient_id=ingredient_pk
        ).first()
        if link is None:
            logger.warning(
                "Remove ingredient failed: ingredient id=%s not in recipe id=%s",
                ingredient_pk,
                pk,
            )
            return not_found(
                f"Інгредієнта з id={ingredient_pk} немає в рецепті з id={pk}."
            )
        link.delete()
        logger.info(
            "Ingredient id=%s removed from recipe id=%s user=%s",
            ingredient_pk,
            pk,
            request.user.username,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
