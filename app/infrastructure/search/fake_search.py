from app.domain.models import StargazingSpot, UserContext
from app.ports.search_provider import SearchProvider


class FakeSearchProvider(SearchProvider):
    """A deterministic search provider for integration tests."""

    def find_spots(self, query: str, ctx: UserContext) -> list[StargazingSpot]:
        return [
            StargazingSpot(
                name="Fake Park 1",
                latitude=48.1,
                longitude=2.1,
                source="fake forum",
                description="A nice dark park. " + query,
                accessibility="Easy by car.",
                safety_assessment="Very safe.",
                bortle_class=4,
            ),
            StargazingSpot(
                name="Fake Hill 2",
                latitude=48.2,
                longitude=2.2,
                source="fake reddit",
                description="High altitude hill.",
                accessibility="Requires hiking.",
                safety_assessment="Watch out for bears.",
                bortle_class=2,
            ),
        ]
