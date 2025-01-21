import json
import graphviz
from pathlib import Path
import sys

def create_recipe_graph(recipe_json: dict) -> graphviz.Digraph:
    """
    Crée un graphe visuel de la recette.
    
    Args:
        recipe_json: Le JSON de la recette
        
    Returns:
        Un graphe Graphviz
    """
    # Crée un nouveau graphe
    dot = graphviz.Digraph(comment='Recipe Structure')
    dot.attr(rankdir='LR')  # Direction gauche à droite
    
    # Styles
    dot.attr('node', shape='box', style='rounded')
    
    # Sous-graphes pour organiser les nœuds
    with dot.subgraph(name='cluster_0') as ingredients:
        ingredients.attr(label='Ingredients')
        ingredients.attr('node', fillcolor='lightblue', style='filled,rounded')
        # Ajoute les ingrédients
        for ing in recipe_json['ingredients']:
            ingredients.node(ing['id'], f"{ing['name']}\n({ing['category']})")
    
    with dot.subgraph(name='cluster_1') as steps:
        steps.attr(label='Steps')
        steps.attr('node', fillcolor='lightgreen', style='filled,rounded')
        # Ajoute les étapes
        for step in recipe_json['steps']:
            step_label = f"Step {step['id']}\n{step['action'][:30]}...\n{step['time']}"
            steps.node(step['id'], step_label)
    
    # Collecte tous les states uniques
    states = {}
    for step in recipe_json['steps']:
        state = step['output_state']
        state_id = state['id']
        if state_id not in states:
            states[state_id] = state
    
    # Ajoute l'état final aux states s'il n'y est pas déjà
    final_state = recipe_json['final_state']
    if final_state['id'] not in states:
        states[final_state['id']] = final_state
    
    # Crée le sous-graphe des states
    with dot.subgraph(name='cluster_2') as states_graph:
        states_graph.attr(label='States')
        states_graph.attr('node', fillcolor='lightyellow', style='filled,rounded')
        # Ajoute les states uniques
        for state_id, state in states.items():
            state_label = f"{state['name']}\n({state['type']})"
            # L'état final a un style différent
            if state['type'] == 'final':
                states_graph.node(state_id, f"Final: {state['name']}", 
                                fillcolor='lightpink', style='filled,rounded')
            else:
                states_graph.node(state_id, state_label)
    
    # Ajoute les connexions
    for step in recipe_json['steps']:
        # Connexions ingrédients -> étapes
        for input in step['inputs']:
            if input['input_type'] == 'ingredient':
                dot.edge(input['ref_id'], step['id'], 
                        label=f"{input.get('amount', '')} {input.get('unit', '')}")
            elif input['input_type'] == 'state':
                dot.edge(input['ref_id'], step['id'])
        
        # Connexions étapes -> états
        dot.edge(step['id'], step['output_state']['id'])
    
    return dot

def main():
    """Point d'entrée principal."""
    if len(sys.argv) != 2:
        print("Usage: python visualize_recipe.py <recipe_json_file>")
        sys.exit(1)
    
    # Charge le fichier JSON
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        recipe_json = json.load(f)
    
    # Crée le graphe
    dot = create_recipe_graph(recipe_json)
    
    # Sauvegarde le graphe
    output_path = json_path.with_suffix('.pdf')
    dot.render(str(output_path), view=True, cleanup=True)
    print(f"Graph saved to: {output_path}")

if __name__ == "__main__":
    main() 