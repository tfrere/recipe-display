# Recipe display

# To do

- OK MUST HAVE : client: Re-rendre visible le stream dans le progress à l'import

- A la fin d'une generation de recette, on doit arriver sur la page de la recette en question
- Tester la generation de recette textuelle

- OK CLIENT : Quand on remove une recipe, il faut demander au contexte de se rafraichir ou supprimer aussi la recette en question, là on revient a la liste et la recette est tjrs là
- OK résoudre ça : WARNING - Recipe was rejected: Empty image URL in input. Please provide a valid
  image URL for the recipe.

- OK Feature: il faut pouvoir, en mode import de recette en texte, éviter les doublons
  - Server : La route import de recette par text prendra maintenant un titre de recette
  - Batch importer : Le nom du fichier .txt qu'on importe ce sera le nom de la recette a envoyer au serveur
- OK Faire en sorte que quand on demande au LLM le sub-recipe name, il faut pas que le sub recipe principal soit le nom de la recette, ça doit etre autre chose de cohérent
- OK La liste des ingredients en mode normal, il faut qu'elle se split correctement, là c'est pas le cas
- OK Gérer la copie des recettes vers le serveur
- OK Mobile

- OK Importer 100% des recettes du livre de recettes collaboratif de quentin
- OK Importer les recettes ottolenghi
