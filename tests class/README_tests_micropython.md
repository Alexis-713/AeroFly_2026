# Tests unitaires MicroPython separes

Ces fichiers sont faits pour etre lances dans Thonny ou sur l'ESP32 avec
MicroPython. Ils n'utilisent pas `types`, `unittest`, `pathlib`, ni les modules
Python absents de MicroPython.

## Fichiers a envoyer sur l'ESP32

Envoie toujours ce fichier :

```text
aerofly_classes.py
```

Puis envoie et lance un test a la fois :

```text
test_gravity_gnss.py
test_ina3221.py
test_gps_filter.py
test_tracker_app.py
```

## Pourquoi il y a `aerofly_classes.py`

Ton code principal finit par :

```python
app = TrackerApp()
app.start()
```

Donc si un test importe directement le code principal, la boucle infinie se
lance. Pour les tests unitaires, les classes sont placees dans un fichier
separe sans lancement automatique.

## Resultat attendu

Chaque fichier doit finir par afficher :

```text
OK - nom_de_la_classe
```

Si une verification echoue, MicroPython affiche une `AssertionError`.
