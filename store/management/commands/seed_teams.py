# store/management/commands/seed_teams.py

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from store.models import Team

TEAMS = [
    # Premier League (England)
    ("Manchester United", "Premier League"),
    ("Manchester City", "Premier League"),
    ("Liverpool", "Premier League"),
    ("Arsenal", "Premier League"),
    ("Chelsea", "Premier League"),
    ("Tottenham Hotspur", "Premier League"),
    ("Newcastle United", "Premier League"),
    ("Aston Villa", "Premier League"),
    ("West Ham United", "Premier League"),
    ("Everton", "Premier League"),
    ("Leicester City", "Premier League"),
    ("Brighton & Hove Albion", "Premier League"),

    ("Real Madrid", "La Liga"),
    ("Barcelona", "La Liga"),
    ("Atletico Madrid", "La Liga"),
    ("Sevilla", "La Liga"),
    ("Real Sociedad", "La Liga"),
    ("Valencia", "La Liga"),
    ("Villarreal", "La Liga"),
    ("Athletic Bilbao", "La Liga"),

    ("Juventus", "Serie A"),
    ("AC Milan", "Serie A"),
    ("Inter Milan", "Serie A"),
    ("Napoli", "Serie A"),
    ("AS Roma", "Serie A"),
    ("Lazio", "Serie A"),
    ("Atalanta", "Serie A"),
    ("Fiorentina", "Serie A"),

    ("Bayern Munich", "Bundesliga"),
    ("Borussia Dortmund", "Bundesliga"),
    ("RB Leipzig", "Bundesliga"),
    ("Bayer Leverkusen", "Bundesliga"),
    ("Borussia Monchengladbach", "Bundesliga"),
    ("Schalke 04", "Bundesliga"),

    ("Paris Saint-Germain", "Ligue 1"),
    ("Marseille", "Ligue 1"),
    ("Lyon", "Ligue 1"),
    ("Monaco", "Ligue 1"),
    ("Lille", "Ligue 1"),

    ("Ajax", "Eredivisie"),
    ("Porto", "Primeira Liga"),
    ("Benfica", "Primeira Liga"),
    ("Sporting CP", "Primeira Liga"),
    ("Celtic", "Scottish Premiership"),
    ("Rangers", "Scottish Premiership"),

    ("Brazil", "National Team"),
    ("Argentina", "National Team"),
    ("Portugal", "National Team"),
    ("France", "National Team"),
    ("England", "National Team"),
    ("Germany", "National Team"),
    ("Spain", "National Team"),
    ("Uganda Cranes", "National Team"),
    ("Nigeria", "National Team"),
    ("Ghana", "National Team"),
    ("Kenya", "National Team"),

    ("KCCA FC", "Uganda Premier League"),
    ("Vipers SC", "Uganda Premier League"),
    ("SC Villa", "Uganda Premier League"),
    ("URA FC", "Uganda Premier League"),
    ("Express FC", "Uganda Premier League"),
    ("Bul FC", "Uganda Premier League"),
]


class Command(BaseCommand):
    help = "Seed the database with commonly bought club and national teams"

    def handle(self, *args, **options):
        created_count = 0
        skipped = []

        for name, league in TEAMS:
            try:
                with transaction.atomic():
                    _, created = Team.objects.get_or_create(name=name, defaults={"league": league})
                    if created:
                        created_count += 1
            except IntegrityError:
                skipped.append(name)

        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} new teams ({len(TEAMS)} total checked)."))
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped (slug already taken by an existing team, likely a near-duplicate name): "
                    + ", ".join(skipped)
                )
            )