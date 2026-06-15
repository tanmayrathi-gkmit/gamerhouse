import pytest
from django.db.models import ProtectedError

from tests.factories.catalog import GameFactory, GenreFactory


@pytest.mark.django_db
class TestGenreModel:
    def test_genre_creation(self):
        genre = GenreFactory(name="Action RPG")
        assert genre.name == "Action RPG"
        assert genre.id is not None
        assert genre.created_at is not None

    def test_genre_deletion_protected(self):
        genre = GenreFactory()
        # GameFactory by default creates a Genre, so we override it
        GameFactory(genre=genre)

        with pytest.raises(ProtectedError):
            genre.delete()

    def test_genre_deletion_allowed(self):
        genre = GenreFactory()
        genre.delete()

        assert genre.deleted_at is not None
        from catalog.models import Genre

        assert Genre.objects.filter(id=genre.id).count() == 0
        assert Genre.all_objects.filter(id=genre.id).count() == 1
