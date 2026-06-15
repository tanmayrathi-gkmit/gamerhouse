import factory

from catalog.models import Game, Genre, Platform


class GenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Genre

    name = factory.Sequence(lambda n: f"Genre {n}")


class PlatformFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Platform

    name = factory.Sequence(lambda n: f"Platform {n}")


class GameFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Game
        skip_postgeneration_save = True

    title = factory.Sequence(lambda n: f"Game {n}")
    description = factory.Faker("text")
    release_date = factory.Faker("date_this_decade")
    genre = factory.SubFactory(GenreFactory)

    @factory.post_generation
    def platforms(self, create, extracted, **kwargs):
        """
        Populate the game's `platforms` many-to-many relationship after the factory creates a Game instance.
        
        Parameters:
            create (bool): If False, the instance was not persisted and no relationship changes are applied.
            extracted (iterable|None): If provided, an iterable of Platform instances to add; if None, a single default Platform is created and added.
        """
        if not create:
            return

        if extracted:
            for platform in extracted:
                self.platforms.add(platform)
        else:
            # Default to one platform if none provided
            self.platforms.add(PlatformFactory())
