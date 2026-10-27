from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import Category, Ingredient, Recipe, RecipeIngredient
from recipes.serializers import (
    CategorySerializer,
    IngredientSerializer,
    RecipeDetailSerializer,
    RecipeIngredientCreateSerializer,
    RecipeListSerializer,
    RecipeSerializer,
)


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


class CategoryListView(APIView):
    def get(self, request):
        categories = Category.objects.all()
        search = request.query_params.get("search")
        if search:
            categories = categories.filter(name__icontains=search)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if not serializer.is_valid():
            return invalid_data(serializer)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    def get(self, request, pk):
        category = get_or_none(Category, pk)
        if category is None:
            return not_found(f"Категорію з id={pk} не знайдено.")
        return Response(CategorySerializer(category).data)

    def put(self, request, pk):
        category = get_or_none(Category, pk)
        if category is None:
            return not_found(f"Категорію з id={pk} не знайдено.")
        serializer = CategorySerializer(category, data=request.data)
        if not serializer.is_valid():
            return invalid_data(serializer)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        category = get_or_none(Category, pk)
        if category is None:
            return not_found(f"Категорію з id={pk} не знайдено.")
        recipes_count = category.recipes.count()
        if recipes_count:
            return error_response(
                f"Неможливо видалити категорію «{category.name}», "
                f"бо до неї належить рецептів: {recipes_count}. "
                "Спочатку видаліть ці рецепти або перенесіть їх в іншу категорію.",
                status.HTTP_409_CONFLICT,
            )
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientListView(APIView):
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
            return invalid_data(serializer)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IngredientDetailView(APIView):
    def get(self, request, pk):
        ingredient = get_or_none(Ingredient, pk)
        if ingredient is None:
            return not_found(f"Інгредієнт з id={pk} не знайдено.")
        return Response(IngredientSerializer(ingredient).data)

    def put(self, request, pk):
        ingredient = get_or_none(Ingredient, pk)
        if ingredient is None:
            return not_found(f"Інгредієнт з id={pk} не знайдено.")
        serializer = IngredientSerializer(ingredient, data=request.data)
        if not serializer.is_valid():
            return invalid_data(serializer)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        ingredient = get_or_none(Ingredient, pk)
        if ingredient is None:
            return not_found(f"Інгредієнт з id={pk} не знайдено.")
        recipes_count = ingredient.recipe_ingredients.count()
        if recipes_count:
            return error_response(
                f"Неможливо видалити інгредієнт «{ingredient.name}», "
                f"бо він використовується в рецептах: {recipes_count}. "
                "Спочатку приберіть його з цих рецептів.",
                status.HTTP_409_CONFLICT,
            )
        ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


RECIPE_ORDERING = ["time_minutes", "-time_minutes", "calories", "-calories"]


class RecipeListView(APIView):
    def get(self, request):
        recipes = Recipe.objects.all()
        params = request.query_params

        for name in ("category", "ingredient", "max_time"):
            value = params.get(name)
            if value and not value.isdigit():
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
            return invalid_data(serializer)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecipeDetailView(APIView):
    def get(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            return not_found(f"Рецепт з id={pk} не знайдено.")
        return Response(RecipeDetailSerializer(recipe).data)

    def put(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            return not_found(f"Рецепт з id={pk} не знайдено.")
        serializer = RecipeSerializer(recipe, data=request.data)
        if not serializer.is_valid():
            return invalid_data(serializer)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            return not_found(f"Рецепт з id={pk} не знайдено.")
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeIngredientListView(APIView):
    def post(self, request, pk):
        recipe = get_or_none(Recipe, pk)
        if recipe is None:
            return not_found(f"Рецепт з id={pk} не знайдено.")
        serializer = RecipeIngredientCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return invalid_data(serializer)
        ingredient = serializer.validated_data["ingredient"]
        if recipe.recipe_ingredients.filter(ingredient=ingredient).exists():
            return error_response(
                f"Інгредієнт «{ingredient.name}» уже є в рецепті "
                f"«{recipe.title}». Щоб змінити кількість, видаліть його "
                "і додайте знову.",
                status.HTTP_409_CONFLICT,
            )
        serializer.save(recipe=recipe)
        return Response(
            RecipeDetailSerializer(recipe).data,
            status=status.HTTP_201_CREATED,
        )


class RecipeIngredientDetailView(APIView):
    def delete(self, request, pk, ingredient_pk):
        link = RecipeIngredient.objects.filter(
            recipe_id=pk, ingredient_id=ingredient_pk
        ).first()
        if link is None:
            return not_found(
                f"Інгредієнта з id={ingredient_pk} немає в рецепті з id={pk}."
            )
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
