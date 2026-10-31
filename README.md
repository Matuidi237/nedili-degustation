# Dégustation NEDILI

Page mobile de notation des produits pendant les dégustations. Le visiteur scanne le code QR, touche les produits goûtés, les note en quelques secondes, et peut laisser son contact.

## Contenu

- `public/index.html` : la page visiteurs. Écran de chargement, puis catégories, produits de la catégorie, notation par émojis (😖 Bof à 🤩 Top, enregistrée de 1 à 5), et remerciement
- `public/admin.html` : les résultats en direct, l'export CSV et le générateur de code QR (accès `/admin`)
- `public/products.json` : **la liste des produits à modifier** (catégories, noms, descriptions, précisions proposées)
- `public/img/logo.webp` : le logo NEDILI (pas encore utilisé dans les pages)
- `server.js` : serveur Node sans dépendance, les données sont enregistrées dans `data/`

## Photos et couleurs

- Chaque gamme (`categories`) a une couleur de carte (`color`) et une couleur de texte (`ink`), utilisées par les cartes défilantes de l'accueil.
- Chaque catégorie a une photo (`image`) affichée sur l'accueil, chaque produit une photo affichée dans la liste et en grand sur sa fiche de notation.
- Ajoutez `"image"` à une gamme pour placer une photo dans sa carte d'accueil.
- Pour un rendu soigné, utilisez des photos détourées (fond transparent, PNG ou WebP), cadrées de face, environ 800 px de côté.

## Numéros des produits

Chaque produit reçoit un numéro (01, 02, 03…) selon son ordre dans `products.json`. Affichez ces numéros sur le stand, à côté de chaque pot ou bouteille : le visiteur retrouve ainsi le produit goûté d'un coup d'œil. Si vous changez l'ordre de la liste, les numéros changent aussi.

## Fiche papier

`print/fiche-degustation.pdf` est une fiche A4 en noir et blanc pour les visiteurs qui préfèrent noter à la main. Elle reprend les produits de `products.json`, avec les mêmes numéros. Le code QR s'imprime à part. Pour régénérer la fiche après un changement de produits :

```powershell
python -m pip install --user reportlab
python print/fiche.py
```

## Lancer en local

```powershell
$env:ADMIN_KEY = "ma-cle-secrete"; node server.js
```

Puis ouvrir http://localhost:3100 (visiteurs) et http://localhost:3100/admin (résultats).

Après l'envoi, la page se remet à zéro toute seule : chaque participant scanne le code QR avec son téléphone et part d'un sondage vierge. Pour effacer un parcours en cours pendant vos tests, ouvrir http://localhost:3100/?nouveau. Pour repartir de résultats vides, supprimer `data/ratings.jsonl` et `data/contacts.jsonl`.

## Déployer sur le VPS (Docker + Nginx Proxy Manager)

Sur le VPS (Ubuntu) :

```bash
cd /opt && git clone https://github.com/Matuidi237/nedili-degustation.git && cd nedili-degustation
echo "ADMIN_KEY=une-cle-longue-et-secrete" > .env
docker compose up -d --build
```

1. Chez le registrar du domaine, créer un enregistrement DNS `A` (ex. `degustation`) vers l'IP du VPS.
2. Dans Nginx Proxy Manager, créer un proxy host pour ce nom vers `nedili-degustation`, port `3000`, avec certificat SSL Let's Encrypt et « Force SSL ».
3. Ouvrir `https://<adresse>/admin`, saisir la clé `ADMIN_KEY`, vérifier l'adresse et télécharger le code QR.

Mise à jour : `git pull && docker compose up -d --build`.

## Où sont les données

Les réponses du formulaire en ligne sont enregistrées sur le VPS, dans le volume Docker `nedili-data` (fichiers `ratings.jsonl` et `contacts.jsonl`). Elles survivent aux redémarrages et aux mises à jour du conteneur. Elles ne sont ni dans Git ni chez un service tiers.

- Consulter : page `/admin` (résultats et contacts), export CSV pour Excel.
- Sauvegarder : `docker cp nedili-degustation:/app/data ./sauvegarde-nedili`
- Attention : `docker compose down -v` supprime le volume, donc les réponses.

## Bon à savoir

- Si le réseau du salon décroche, les notes restent en attente sur le téléphone et partent dès le retour de la connexion.
- Comme un panier : les notes restent sur le téléphone, modifiables ou retirables, jusqu'à ce que le visiteur touche « Envoyer mes notes ». Après l'envoi, le téléphone repart sur un sondage vierge.
- Le CSV s'ouvre directement dans Excel (séparateur point-virgule).
