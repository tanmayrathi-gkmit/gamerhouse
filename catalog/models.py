from django.db import models
from django.db.models import ProtectedError

from core.models import BaseModel


class Genre(BaseModel):
    """
    Represents a game genre.

    Used as a reference entity to categorize games.
    Each genre has a unique, human-readable name.
    """

    name = models.CharField(max_length=255)

    class Meta:
        db_table = "genres"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        """
        Override delete to respect on_delete=PROTECT for soft deletes.

        Raises ProtectedError if any active games reference this genre.
        """
        if self.games.exists():
            raise ProtectedError(
                "Cannot delete Genre because it is referenced by active Games.",
                [self],
            )
        super().delete(*args, **kwargs)


class Platform(BaseModel):
    """
    Represents a gaming platform.

    Used as a reference entity to identify supported platforms
    such as PC, console, or mobile.
    Each platform has a unique name.
    """

    name = models.CharField(max_length=255)

    class Meta:
        db_table = "platforms"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        """
        Override delete to prevent deletion if referenced by active games.

        Raises ProtectedError if any active games use this platform.
        """
        if self.games.exists():
            raise ProtectedError(
                "Cannot delete Platform because it is referenced by active Games.",
                [self],
            )
        super().delete(*args, **kwargs)


class Game(BaseModel):
    """
    Represents a game with genre and platform associations.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    release_date = models.DateField(blank=True, null=True)
    genre = models.ForeignKey(
        "catalog.Genre", related_name="games", on_delete=models.PROTECT
    )
    platforms = models.ManyToManyField("catalog.Platform", related_name="games")

    class Meta:
        db_table = "games"
        ordering = ["title"]

    def __str__(self):
        return self.title
