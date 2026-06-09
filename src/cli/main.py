"""Rich-based CLI interface for vn-real-estate-scout."""
from typing import Optional, Dict, Any, List
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.text import Text

console = Console()


class RealEstateCLI:
    """Interactive CLI for vn-real-estate-scout."""

    def __init__(self):
        """Initialize CLI."""
        self.console = console
        self.preferences = {}

    def display_welcome(self):
        """Display welcome message."""
        welcome_text = """
╔══════════════════════════════════════════════════════════════╗
║     vn-real-estate-scout                                     ║
║     AI-powered Vietnam Real Estate Intelligence Agent         ║
╚══════════════════════════════════════════════════════════════╝

Find genuine listings, skip the noise.

This agent scrapes multiple Vietnamese platforms, extracts property
details using PhoBERT NER, removes duplicates, checks flood zones,
and delivers a curated Top 5 shortlist.
        """
        self.console.print(Panel(welcome_text, style="bold blue"))

    def collect_preferences(self) -> Dict[str, Any]:
        """Collect user search preferences interactively.

        Returns:
            Dictionary of user preferences
        """
        self.console.print("\n[bold cyan]Tell us what you're looking for:[/bold cyan]\n")

        preferences = {}

        # Budget
        self.console.print("[yellow]Budget[/yellow]")
        min_price = Prompt.ask("  Minimum price (VND, e.g., 1000000000)", default="0")
        max_price = Prompt.ask("  Maximum price (VND, e.g., 3000000000)", default="")
        preferences['min_price'] = float(min_price) if min_price else None
        preferences['max_price'] = float(max_price) if max_price else None

        # Location
        self.console.print("\n[yellow]Location[/yellow]")
        city = Prompt.ask("  City", choices=["Ho Chi Minh City", "Hanoi", "Da Nang"], default="Ho Chi Minh City")
        preferences['preferred_cities'] = [city]
        district = Prompt.ask("  District (e.g., Quan 1, Quan 7)", default="")
        if district:
            preferences['preferred_districts'] = [district]

        # Property type
        self.console.print("\n[yellow]Property Type[/yellow]")
        property_type = Prompt.ask(
            "  What are you looking for?",
            choices=["apartment", "house", "land", "commercial"],
            default="apartment"
        )
        preferences['property_types'] = [property_type]

        # Area
        self.console.print("\n[yellow]Size[/yellow]")
        min_area = Prompt.ask("  Minimum area (m2)", default="50")
        max_area = Prompt.ask("  Maximum area (m2)", default="")
        preferences['min_area'] = float(min_area) if min_area else None
        preferences['max_area'] = float(max_area) if max_area else None

        # Bedrooms
        self.console.print("\n[yellow]Bedrooms[/yellow]")
        bedrooms_min = Prompt.ask("  Minimum bedrooms", default="2")
        preferences['bedrooms_min'] = int(bedrooms_min) if bedrooms_min else None

        # Commute
        self.console.print("\n[yellow]Commute[/yellow]")
        workplace_lat = Prompt.ask("  Workplace latitude (optional, press Enter to skip)", default="")
        workplace_lon = Prompt.ask("  Workplace longitude (optional, press Enter to skip)", default="")
        if workplace_lat and workplace_lon:
            preferences['workplace_latitude'] = float(workplace_lat)
            preferences['workplace_longitude'] = float(workplace_lon)
            max_commute = Prompt.ask("  Maximum commute time (minutes)", default="45")
            preferences['max_commute_minutes'] = int(max_commute)

        # Flood preference
        self.console.print("\n[yellow]Other Preferences[/yellow]")
        avoid_flood = Confirm.ask("  Avoid flood-prone areas?", default=True)
        preferences['avoid_flood_risk'] = avoid_flood

        self.preferences = preferences
        return preferences

    def display_results(self, results: Dict[str, Any]):
        """Display search results in a formatted table.

        Args:
            results: Agent result dictionary
        """
        self.console.print("\n[bold green]Search Complete![/bold green]\n")

        # Summary
        summary = f"""
Found: {results.get('total_listings_found', 0)} listings
Genuine: {results.get('genuine_listings_count', 0)} after deduplication
Processing time: {results.get('processing_time_seconds', 0):.1f} seconds
        """
        self.console.print(Panel(summary, style="cyan"))

        # Top candidates table
        candidates = results.get('top_candidates', [])
        if not candidates:
            self.console.print("[yellow]No matching properties found.[/yellow]")
            return

        table = Table(title="\n[bold]Top 5 Recommendations[/bold]")
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Address", style="white")
        table.add_column("Price (VND)", style="green")
        table.add_column("Area (m2)", style="blue")
        table.add_column("Score", style="yellow")
        table.add_column("Flags", style="red")

        for i, prop in enumerate(candidates, 1):
            data = prop.get('property_data', {})
            flags = prop.get('flags', [])
            flag_text = ", ".join(flags) if flags else "✓"

            table.add_row(
                str(i),
                data.get('address', 'N/A')[:30],
                f"{data.get('price_vnd', 0):,.0f}" if data.get('price_vnd') else "N/A",
                str(data.get('area_m2', 'N/A')),
                f"{prop.get('total_score', 0):.1%}",
                flag_text
            )

        self.console.print(table)

        # Detailed view prompt
        self.console.print("\n[dim]Enter a number (1-5) to view details, or 'q' to quit[/dim]")

    def display_property_details(self, property_data: Dict[str, Any]):
        """Display detailed information for a single property.

        Args:
            property_data: Property data dictionary
        """
        details = f"""
[bold cyan]Property Details[/bold cyan]

[yellow]Basic Information[/yellow]
  Address: {property_data.get('address', 'N/A')}
  Price: {property_data.get('price_vnd', 0):,.0f} VND
  Area: {property_data.get('area_m2', 'N/A')} m2
  Type: {property_data.get('property_type', 'N/A')}
  Bedrooms: {property_data.get('bedrooms', 'N/A')}
  Bathrooms: {property_data.get('bathrooms', 'N/A')}

[yellow]Location & Amenities[/yellow]
  District: {property_data.get('district', 'N/A')}
  Legal Status: {property_data.get('legal_status', 'N/A')}
  Furnished: {property_data.get('furnished', 'N/A')}
  Parking: {property_data.get('parking_required', False)}

[yellow]Contact[/yellow]
  Phone: {property_data.get('contact_phone', 'N/A')}
  Agent: {property_data.get('contact_name', 'N/A')}

[yellow]Platform[/yellow]
  Source: {property_data.get('platform', 'N/A')}
  URL: {property_data.get('url', 'N/A')}
        """
        self.console.print(Panel(details, border_style="cyan"))

    def display_progress(self, phase: str, message: str):
        """Display progress message.

        Args:
            phase: Current phase name
            message: Progress message
        """
        self.console.print(f"[dim]{phase}:[/dim] {message}")

    def display_error(self, error: str):
        """Display error message.

        Args:
            error: Error message
        """
        self.console.print(f"[red]Error: {error}[/red]")


def main():
    """Main CLI entry point."""
    cli = RealEstateCLI()
    cli.display_welcome()

    # Collect preferences
    preferences = cli.collect_preferences()

    # Confirm
    cli.console.print("\n[bold cyan]Ready to search![/bold cyan]")
    if not Confirm.ask("Start search now?", default=True):
        cli.console.print("[yellow]Search cancelled.[/yellow]")
        return

    # Run agent (placeholder)
    cli.console.print("\n[green]Starting search...[/green]")
    cli.display_progress("Scraping", "Fetching listings from platforms")

    # Placeholder results
    results = {
        'total_listings_found': 0,
        'genuine_listings_count': 0,
        'processing_time_seconds': 0.0,
        'top_candidates': []
    }

    cli.display_results(results)


if __name__ == "__main__":
    main()
