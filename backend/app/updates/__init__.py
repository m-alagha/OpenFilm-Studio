"""In-app update manager (M1.5).

Discovers new versions from the official repository's GitHub Releases and gives
installation-specific guidance. It never downloads or runs release assets on its
own; one-click installation stays disabled until signed installers exist (D9).
"""

REPOSITORY = "m-alagha/OpenFilm-Studio"
