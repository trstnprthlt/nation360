# Visite virtuelle 360° d'une gare (style Street View + plan)

Déplacement de photo 360° en photo 360° (flèches au sol), avec un **volet de plan à gauche** :
plan du niveau actif, position de l'utilisateur, tous les autres points de vue cliquables,
liste des niveaux et recherche par mot-clé.
Basé sur [Photo Sphere Viewer](https://photo-sphere-viewer.js.org). Aucune installation, aucun Python :
ce sont des fichiers statiques que GitHub Pages publie tels quels.

## Le volet de gauche

- **Ouvert par défaut**, il occupe 1/3 de l'écran. Le bouton « ◀ Masquer le plan » (en haut à gauche de la photo) le replie ;
  « ▶ Plan » le rouvre. On peut aussi tirer son bord droit pour l'élargir. L'état (ouvert/replié) et la largeur sont mémorisés.
- **Plan** : il reste fixe (il ne pivote pas). Un point bleu avec un cône indique votre position et la direction du regard ;
  les points jaunes sont les autres points de vue, les carrés violets sont les escaliers/ascenseurs.
  Clic sur un point = aller à cette photo. Molette = zoom, glisser = déplacer, boutons `+ − ⤢ ◎` (◎ recentre sur vous).
- **Niveaux** : liste déroulante. Consulter un autre niveau ne vous déplace pas ; la liste indique « ● vous êtes ici ».
- **Recherche** : tapez un mot (nom, identifiant ou niveau, sans tenir compte des accents ni des majuscules ; plusieurs mots =
  tous doivent correspondre). La liste des photos s'affiche, un clic (ou ↓ ↑ Entrée) y va directement.
- **Bandeau en haut de la photo** : niveau et nom de la photo active, **toujours visibles, volet ouvert ou replié**.

## 1. Publier le site (une seule fois)

1. Créez un dépôt GitHub **public** (New repository).
2. Envoyez-y tout le **contenu** de ce dossier (Add file > Upload files).
3. Settings > Pages > « Deploy from a branch », branche `main`, dossier `/ (root)`.
4. Au bout d'une à deux minutes, le site est à l'adresse `https://VOTRE-NOM.github.io/NOM-DU-DEPOT/`.

## 2. Ajouter vos photos

- **Photos 360°** : JPG (format 2:1) dans `panos/` (supprimez ceux de la démo). Conseil : 4096×2048, qualité 80-85 %, 1 à 2 Mo.
- **Plans** : une image par niveau dans `plans/`, déclarée dans `data/levels.json`.
- **Tableur** `data/photos.csv` : une ligne par photo. Sur GitHub : ouvrir le fichier puis le crayon pour l'éditer en ligne,
  ou Excel / LibreOffice (enregistrer en CSV UTF-8) puis renvoyer le fichier. Séparateur `;` ou `,`.

| colonne | rôle |
|---|---|
| `id` | identifiant unique (`N1_012`) |
| `nom` | texte affiché dans le bandeau, la recherche et au survol du plan |
| `niveau` | clé du niveau dans `levels.json` (`-1`, `-2`, …) |
| `x`, `y` | position sur le plan (voir « Taille des plans ») |
| `cap` | direction (degrés, sens horaire depuis le **haut du plan**) vers laquelle pointe le **centre de la photo** ; 0 si toutes les photos sont prises face au haut du plan |
| `fichier` | chemin de la photo, ex. `panos/N1_012.jpg` |
| `liens` | (option) ids reliés en plus : escaliers, ascenseurs, photos trop éloignées |
| `bloque` | (option) ids à ne pas relier malgré la proximité (couloirs séparés par un mur) |

Les liens entre photos voisines d'un même niveau sont **calculés automatiquement** : deux photos sont reliées si leur distance
sur le plan est inférieure à `distance_max` (dans `levels.json`, 130 par défaut, à régler selon l'échelle du plan : environ
1,5 fois l'écart entre deux photos). Les escaliers se déclarent dans `liens` (un sens suffit).

Dans `levels.json`, paramétrer chaque plan ainsi : 
"-1": { "nom": "Niveau -1 - Mezzanine", "plan": "plans/niveau-1.jpg", "distance_max": 400, "angle_direction": 45 }
`angle direction` (facultatif, par défaut définit dans `donnees.js` à 30°) : pour les flèches de navigation, on garde une photo voisine seulement si aucune voisine plus proche n'est déjà gardée dans cet angle.

Une erreur dans le tableur (id en double, nombre illisible, lien vers un id inconnu, photo isolée, groupe de photos non relié)
est signalée par un encadré rouge en haut à gauche de la page.

## Taille des plans

- **Aucune limite imposée par le code.** La limite pratique est celle du navigateur : visez **2000 à 4000 pixels** sur le grand côté
  (net même en zoomant), un fichier de **moins de quelques Mo**. Au-delà d'environ 8000 pixels, l'image devient lourde à décoder
  et la page ralentit. Un plan trop grand ne casse rien, il ralentit seulement.
- **PNG** pour un plan dessiné, **JPG** pour un scan, **SVG** pour un plan vectoriel (très léger, net à tout zoom).
- **x, y** sont en pixels de l'image (origine en haut à gauche, y vers le bas), relevés par exemple dans Paint, GIMP ou Photopea.
  Pour un **SVG**, ce sont les unités de son `viewBox` (`viewBox="0 0 1200 800"` : x de 0 à 1200, y de 0 à 800), comme dans
  Inkscape ou Illustrator. Un SVG sans `viewBox` doit avoir `width` et `height` ; sans aucun des deux, un message l'indique.
- Gardez le **même cadrage et la même échelle** pour tous les niveaux : les escaliers relient des photos de niveaux différents,
  et c'est leur position (x, y) qui oriente la flèche.

## 3. Limites de GitHub à connaître

- Un site GitHub Pages ne doit pas dépasser **1 Go**, avec une limite souple de **100 Go de trafic par mois**.
  À 1,5 Mo par photo : environ 600 photos au maximum. Au-delà, réduisez les photos (3000×1500) ou hébergez-les ailleurs.
- Sur la formule gratuite, Pages exige un dépôt **public** : vos photos seront accessibles à tous.
- L'envoi par le navigateur est limité à 25 Mo par fichier ; pour des centaines de photos, utilisez GitHub Desktop.
- Dans une gare, vérifiez l'autorisation de l'exploitant avant de publier des photos.

## 4. Voir le site sur votre ordinateur avant de publier (facultatif)

Un double-clic sur `index.html` ne fonctionne pas (le navigateur bloque le chargement des fichiers).
Il faut un serveur local : l'extension *Live Server* de VS Code, ou `python3 -m http.server 8000`.

## 5. Dossier `dev/` (facultatif, pour développeurs)

- `dev/e2e.py` : test automatique dans un vrai navigateur (Playwright), 63 vérifications sur la démo :
  `pip install playwright pillow && python3 -m playwright install chromium && python3 dev/e2e.py`.
- `dev/make_demo.py` : régénère la démo (**écrase** `data/`, `panos/`, `plans/`).
- `dev/build_nodes.py` : ancienne version Python du calcul des liens, utilisée seulement par `make_demo.py`.

## Limites connues

- Testé avec Chromium (WebGL logiciel) sur des panoramas factices : pas sur de vraies photos, ni sur Safari ou Firefox.
  Conçu pour ordinateur ; pas adapté à un petit écran de téléphone.
- La position `x,y` de chaque photo est saisie à la main (pas de GPS sous terre).
- Pas de fusion des photos : on saute d'un panorama à l'autre avec un fondu, comme Street View.
