# Recipe display

# To do

- Feature: il faut pouvoir, en mode import de recette en texte, éviter les doublons

  - Server : La route import de recette par text prendra maintenant un titre de recette
  - Batch importer : Le nom du fichier .txt qu'on importe ce sera le nom de la recette a envoyer au serveur
  - Client : a l'import d'une recette en mode text, on demande un titre en plus du txt

- Faire en sorte que quand on demande au LLM le sub-recipe name, il faut pas que le sub recipe principal soit le nom de la recette, ça doit etre autre chose de cohérent

- La liste des ingredients en mode normal, il faut qu'elle se split correctement, là c'est pas le cas

- MUST HAVE : client: Re-rendre visible le stream dans le progress à l'import

- Importer 100% des recettes du livre de recettes collaboratif de quentin
- Importer les recettes ottolenghi
