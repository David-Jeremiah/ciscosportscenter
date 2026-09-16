from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Jersey, Team


class JerseySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Jersey.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("store:jersey_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.created_at


class TeamSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Team.objects.all()

    def location(self, obj):
        return reverse("store:team_detail", args=[obj.slug])


class StaticViewSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return ["store:jersey_list"]

    def location(self, item):
        return reverse(item)