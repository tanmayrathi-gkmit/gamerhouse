import pytest
from django.db.models import ProtectedError

from tests.factories.catalog import GameFactory, PlatformFactory


@pytest.mark.django_db
class TestPlatformModel:
    def test_platform_creation(self):
        platform = PlatformFactory(name="PlayStation 5")
        assert platform.name == "PlayStation 5"
        assert platform.id is not None

    def test_platform_deletion_protected(self):
        """
        Verifies that deleting a Platform referenced by a Game is blocked.
        
        Creates a Platform and associates a Game with it, then asserts that attempting to delete the Platform raises django.db.models.deletion.ProtectedError.
        
        Raises:
            ProtectedError: If the Platform has related Game objects, deletion is prevented.
        """
        platform = PlatformFactory()
        # GameFactory post_generation adds a platform by default if none provided
        GameFactory(platforms=[platform])

        with pytest.raises(ProtectedError):
            platform.delete()

    def test_platform_deletion_allowed(self):
        """
        Verifies that deleting an unreferenced Platform performs a soft delete and updates managers appropriately.
        
        Asserts that the instance's `deleted_at` is set, that the default manager no longer returns the object, and that the `all_objects` manager still includes the deleted record.
        """
        platform = PlatformFactory()
        platform.delete()

        assert platform.deleted_at is not None
        from catalog.models import Platform

        assert Platform.objects.filter(id=platform.id).count() == 0
        assert Platform.all_objects.filter(id=platform.id).count() == 1
