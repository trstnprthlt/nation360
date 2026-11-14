# Visite virtuelle 360° d'une gare (style Street View + plan)

Déplacement de photo 360° en photo 360° (flèches au sol) avec un **plan cliquable par niveau**.
Basé sur [Photo Sphere Viewer](https://photo-sphere-viewer.js.org) (plugins *Virtual Tour* et *Map*).
Aucune installation, aucun Python : ce sont des fichiers statiques que GitHub Pages publie tels quels.

## 1. Publier le site (une seule fois)

1. Créez un dépôt GitHub **public** (New repository).
2. Envoyez-y tout le contenu de ce dossier (Add file > Upload files, en glissant les fichiers).
3. Settings > Pages > « Deploy from a branch », branche `main`, dossier `/ (root)`.
4. Au bout d'une à deux minutes, le site est à l'adresse `https://VOTRE-NOM.github.io/NOM-DU-DEPOT/`.

## 2. Ajouter vos photos

- Photos 360° : fichiers JPG (format 2:1) à mettre dans `panos/` (supprimez ceux de la démo).
  Conseil : 4096×2048, qualité 80-85 %, soit environ 1 à 2 Mo par photo.
- Plans : une image par niveau dans `plans/`, déclarée dans `data/levels.json`.
- Tableur `data/photos.csv` : une ligne par photo.
  Sur GitHub, ouvrez le fichier puis le crayon pour le modifier en ligne, ou éditez-le dans Excel / LibreOffice
  (enregistrer au format CSV UTF-8) et renvoyez-le. Séparateur `;` ou `,`, les deux sont acceptés.

| colonne | rôle |
|---|---|
| `id` | identifiant unique (`N1_012`) |
| `nom` | texte affiché en bas de l'écran et au survol du plan |
| `niveau` | clé du niveau dans `levels.json` (`-1`, `-2`, …) |
| `x`, `y` | position sur le plan, en **pixels de l'image** (origine en haut à gauche) |
| `cap` | direction (degrés, sens horaire depuis le **haut du plan**) vers laquelle pointe le **centre de la photo** ; 0 si toutes vos photos sont prises face au haut du plan |
| `fichier` | chemin de la photo, ex. `panos/N1_012.jpg` |
| `liens` | (option) ids reliés en plus : escaliers, ascenseurs, photos trop éloignées |
| `bloque` | (option) ids à ne pas relier malgré la proximité (couloirs séparés par un mur) |

Les liens entre photos voisines d'un même niveau sont **calculés automatiquement** par la page :
deux photos sont reliées si leur distance sur le plan est inférieure à `distance_max` (en pixels, réglable
par niveau dans `levels.json`, 130 par défaut). Les escaliers se déclarent dans `liens` (un sens suffit).

Si le tableur contient une erreur (id en double, nombre illisible, lien vers un id inconnu, photo isolée,
groupe de photos non relié), un encadré rouge l'indique en haut à gauche de la page.
Astuce : relevez `x,y` avec un éditeur d'images qui affiche les coordonnées du curseur.

## 3. Limites de GitHub à connaître

- Un site GitHub Pages ne doit pas dépasser **1 Go** et a une limite souple de **100 Go de trafic par mois**.
  À 1,5 Mo par photo, cela fait environ 600 photos au maximum ; une visite en charge quelques dizaines
  (30 à 70 Mo). Pour une très grande gare, réduisez les photos (3000×1500) ou hébergez-les ailleurs.
- Sur la formule gratuite de GitHub, Pages exige un dépôt **public** : vos photos seront accessibles à tous.
- Envoyer des fichiers par le navigateur est limité à 25 Mo par fichier ; pour des centaines de photos
  d'un coup, utilisez GitHub Desktop (application gratuite, glisser-déposer).
- Dans une gare, vérifiez l'autorisation de l'exploitant avant de publier des photos.

## 4. Voir le site sur votre ordinateur avant de publier (facultatif)

Un double-clic sur `index.html` ne fonctionne pas (le navigateur bloque le chargement des fichiers).
Il faut un serveur local : l'extension *Live Server* de VS Code, ou `python3 -m http.server 8000`.

## 5. Dossier `dev/` (facultatif, pour développeurs)

- `dev/e2e.py` : test automatique dans un vrai navigateur (Playwright) ; voir l'en-tête du fichier.
- `dev/make_demo.py` : régénère la démo (**écrase** `data/`, `panos/`, `plans/`).
- `dev/build_nodes.py` : ancienne version Python du calcul des liens, utilisée seulement par `make_demo.py`.

## Limites connues

- Testé avec Chromium (WebGL logiciel) sur des panoramas factices, pas sur de vraies photos ni sur Safari / mobile.
- Un seul plan affiché à la fois ; la liste des niveaux saute à la première photo du niveau choisi.
- La position `x,y` de chaque photo est saisie à la main (pas de GPS sous terre).
- Pas de fusion des photos : on saute d'un panorama à l'autre avec un fondu, comme Street View.

## Licences

Code de ce dépôt : MIT. `vendor/` : Photo Sphere Viewer 5.15.1 et three.js (MIT), voir `vendor/VERSIONS.txt`.
