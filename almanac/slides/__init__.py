"""Almanac slide modules. Each module exports a Slide-protocol instance as `slide`."""

from almanac.slides.authors import slide as authors_slide
from almanac.slides.cadence import slide as cadence_slide
from almanac.slides.cover import slide as cover_slide
from almanac.slides.languages import slide as languages_slide
from almanac.slides.numbers import slide as numbers_slide
from almanac.slides.top_files import slide as top_files_slide
from almanac.slides.verbs import slide as verbs_slide

SLIDES = [
    cover_slide,
    numbers_slide,
    cadence_slide,
    top_files_slide,
    languages_slide,
    verbs_slide,
    authors_slide,
]

__all__ = ["SLIDES"]
