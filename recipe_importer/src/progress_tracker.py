import asyncio
from datetime import datetime
from typing import Dict, List, Tuple
from rich.console import Console

from .models import RecipeError, RecipeProgress


class ProgressTracker:
    """Classe responsable du suivi et de l'affichage de la progression des importations."""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.recent_updates = []
        self.last_error = None
    
    async def track_progress(self, stats: Dict, start_time: datetime, updates_queue: asyncio.Queue) -> None:
        """Affiche périodiquement les statistiques d'importation."""
        try:
            last_update_time = datetime.now()
            
            while True:
                # Traiter les mises à jour de la queue
                try:
                    while True:
                        # Non-bloquant, récupère jusqu'à 10 mises à jour d'un coup
                        update = updates_queue.get_nowait()
                        self.recent_updates.append(update)
                        
                        # Capturer la dernière erreur s'il y en a une
                        url, status, message = update
                        if status == "error":
                            self.last_error = (url, message, datetime.now())
                            
                        if len(self.recent_updates) > 10:
                            self.recent_updates.pop(0)
                        updates_queue.task_done()
                except asyncio.QueueEmpty:
                    pass
                
                # Ne mettre à jour l'affichage qu'une fois par seconde maximum
                now = datetime.now()
                if (now - last_update_time).total_seconds() < 1:
                    await asyncio.sleep(0.1)
                    continue
                
                last_update_time = now
                self._update_display(stats, start_time, now)
                
                # Faire une pause avant la prochaine mise à jour
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.console.print(f"[red]Error updating display: {str(e)}[/red]")
    
    def _update_display(self, stats: Dict, start_time: datetime, now: datetime) -> None:
        """Updates the display with current statistics."""
        elapsed = now - start_time
        elapsed_str = str(elapsed).split('.')[0]
        
        # Calculate completion percentage
        completed = stats["success"] + stats["errors"] + stats["skipped"]
        completion_pct = int((completed / stats["total"]) * 100) if stats["total"] > 0 else 0
        
        # Calculate waiting tasks
        stats["waiting"] = stats["total"] - completed - stats["in_progress"]
        
        # Estimate total time based on current progress
        est_total_time = "--:--:--"
        if completion_pct > 0:
            # Calculate the estimated total time based on elapsed time and completion percentage
            est_total_seconds = (elapsed.total_seconds() / completion_pct) * 100
            est_remaining_seconds = est_total_seconds - elapsed.total_seconds()
            
            # Format the estimated total time
            m, s = divmod(int(est_remaining_seconds), 60)
            h, m = divmod(m, 60)
            est_total_time = f"{h:d}:{m:02d}:{s:02d}"
        
        # Clear previous display and redraw
        self.console.clear()
        
        # Standardize width for all display elements
        display_width = 80  # Total display width
        separator_line = "[dim]" + "═" * display_width + "[/dim]"
        simple_separator = "[dim]" + "─" * display_width + "[/dim]"
        double_separator = "[dim]" + "═" * display_width + "[/dim]"
        
        # Préparer les métadonnées pour les aligner à droite
        metadata = (
            f"[dim]URLs[/dim] [yellow]{stats['total']}[/yellow] [dim]|[/dim] "
            f"[dim]Concurrent[/dim] [yellow]{stats.get('concurrent_imports', 5)}[/yellow] [dim]|[/dim] "
            f"[dim]Time[/dim] [yellow]{elapsed_str}[/yellow] [dim]|[/dim] "
            f"[dim]Est[/dim] [yellow]{est_total_time}[/yellow]"
        )
        
        # Calculer l'espace nécessaire pour aligner le metadata à droite
        title = "[bold cyan]Recipe Importer[/bold cyan]"
        title_length = len("Recipe Importer")  # Longueur sans les tags de formatage
        metadata_length = len(metadata.replace("[dim]", "").replace("[/dim]", "")
                             .replace("[yellow]", "").replace("[/yellow]", ""))
        
        # Calculer l'espace entre le titre et les métadonnées
        spacing = display_width - title_length - metadata_length
        spacing = max(1, spacing)  # Assurer au moins un espace
        
        # Display header with title and metadata on the same line
        self.console.print("\n")
        # self.console.print("")  # Espace supplémentaire avant le titre
        
        # Afficher le titre à gauche et les métadonnées à droite
        self.console.print(f"{title}{' ' * spacing}{metadata}")
        
        # self.console.print("")  # Espace supplémentaire après le titre
        self.console.print(separator_line)
        
        # Calculate the exact width needed for labels and numbers
        prefix = f"[bold white]{completion_pct}[/bold white] [dim]%[/dim] "  # Le pourcentage est maintenant au début avec % en dim
        suffix = f" [bold white]{completed}[/bold white][dim]/{stats['total']}[/dim]"  # Le compteur est maintenant à la fin
        
        # Calculate the available space for progress bar
        # Retirer toutes les balises de formatage pour calculer la longueur réelle
        prefix_length = len(prefix.replace("[bold white]", "").replace("[/bold white]", "").replace("[dim]", "").replace("[/dim]", ""))
        suffix_length = len(suffix.replace("[bold white]", "").replace("[/bold white]", "").replace("[dim]", "").replace("[/dim]", ""))
        available_width = display_width - prefix_length - suffix_length
        
        # Calculate proportional widths of each segment within the available space
        total = stats["total"]
        if total > 0:
            success_width = int((stats["success"] / total) * available_width)
            errors_width = int((stats["errors"] / total) * available_width)
            skipped_width = int((stats["skipped"] / total) * available_width)
            in_progress_width = int((stats["in_progress"] / total) * available_width)
            waiting_width = available_width - success_width - errors_width - skipped_width - in_progress_width
        else:
            success_width = errors_width = skipped_width = in_progress_width = 0
            waiting_width = available_width
        
        # Style plus moderne pour la barre de progression
        # Utiliser des caractères Unicode plus esthétiques pour un look plus élégant
        bar_complete_char = "▮"  # Utiliser le même caractère que pour les recettes
        bar_empty_char = "▯"     # Utiliser le même caractère que pour les recettes
        
        # Build the progress bar with fixed width components and modern style
        segments = []
        if success_width > 0:
            segments.append(f"[bold green]{bar_complete_char * success_width}[/bold green]")
        if errors_width > 0:
            segments.append(f"[bold red]{bar_complete_char * errors_width}[/bold red]")
        if skipped_width > 0:
            segments.append(f"[bold yellow]{bar_complete_char * skipped_width}[/bold yellow]")
        if in_progress_width > 0:
            segments.append(f"[bold blue]{bar_complete_char * in_progress_width}[/bold blue]")
        if waiting_width > 0:
            segments.append(f"[dim white]{bar_empty_char * waiting_width}[/dim white]")
            
        progress_bar = "".join(segments)
        
        # Display the progress bar with precise spacing and modern styling
        self.console.print(f"{prefix}{progress_bar}{suffix}")
        self.console.print(simple_separator)
        
        # Print status counters
        self.console.print(
            f"[green]Success {stats['success']}[/green] [dim]|[/dim] "
            f"[red]Errors {stats['errors']}[/red] [dim]|[/dim] "
            f"[yellow]Skipped {stats['skipped']}[/yellow] [dim]|[/dim] "
            f"[blue]In Progress {stats['in_progress']}[/blue] [dim]|[/dim] "
            f"[dim white]Waiting {stats['waiting']}[/dim white]"
        )
        
        # Ajouter un séparateur double après les compteurs
        self.console.print(double_separator)
        
        # Missing tasks warning (only if needed)
        if "completed" in stats:
            total_completed = stats["success"] + stats["errors"] + stats["skipped"]
            if stats["completed"] > total_completed:
                missing = stats["completed"] - total_completed
                self.console.print(f"[red]Warning {missing} completed tasks not counted correctly![/red]")
        
        # Display active recipes and latest error
        self._display_in_progress_recipes(stats, display_width)
        self._display_latest_error(now, display_width, simple_separator, double_separator)
    
    def _display_in_progress_recipes(self, stats: Dict, display_width: int = 80) -> None:
        """Displays currently processing recipes."""
        if stats["in_progress"] > 0:
            # Définir les types de séparateurs
            double_separator = "[dim]" + "═" * display_width + "[/dim]"
            
            self.console.print("\n[bold cyan]Active Recipes[/bold cyan]")
            self.console.print(double_separator)  # Séparateur double à la place du simple
            
            # Create a dictionary to gather the latest updates by URL
            in_progress_recipes = {}
            recipe_steps = {}
            recipe_progress = {}
            
            # Collect the most recent information for each recipe in progress
            for update in self.recent_updates:
                url, status, message = update
                
                # Filter only recipes that are actually being processed
                if status not in ["success", "error", "skipped"]:
                    # For recipes in progress, keep the latest update
                    short_url = url[:60] + "..." if len(url) > 60 else url
                    
                    # If the message contains a step, extract it
                    if "step:" in message.lower():
                        step = message.split("step:")[-1].strip()
                        recipe_steps[short_url] = step
                    
                    # Calculate (approximate) progress based on steps
                    if "structure" in message.lower() or "structure" in (recipe_steps.get(short_url, "").lower()):
                        recipe_progress[short_url] = 50
                    elif "scrape" in message.lower() or "scrape" in (recipe_steps.get(short_url, "").lower()):
                        recipe_progress[short_url] = 25
                    elif "import" in message.lower() and "success" in message.lower():
                        recipe_progress[short_url] = 100
                    else:
                        recipe_progress[short_url] = recipe_progress.get(short_url, 10)
                    
                    # Store messages to display (only for active recipes)
                    if "Waiting for semaphore" not in message:
                        in_progress_recipes[short_url] = (status, message)
            
            # Display recipes in progress
            if in_progress_recipes:
                # Use the same progress bar width as the main bar
                progress_width = 15  # Barre de progression plus petite
                name_width = 40      # Plus d'espace pour le nom
                
                active_count = 0
                for i, (short_url, (status, message)) in enumerate(in_progress_recipes.items()):
                    # Determine current step
                    current_step = recipe_steps.get(short_url, "processing")
                    
                    # Estimate progress
                    progress = recipe_progress.get(short_url, 10)
                    
                    # Determine the right indicator based on message or step
                    if "scrape" in message.lower() or "scrape" in current_step.lower():
                        step_indicator = "📥"  # Data retrieval
                        emoji_color = "blue"
                        current_step_display = "Scraping"
                    elif "structur" in message.lower() or "structur" in current_step.lower():
                        step_indicator = "🔄"  # Data structuring
                        emoji_color = "yellow"
                        current_step_display = "Structuring"
                    elif "import" in message.lower() and "success" in message.lower():
                        step_indicator = "✅"  # Successful import
                        emoji_color = "green"
                        current_step_display = "Importing"
                    else:
                        step_indicator = "⏳"  # Generic visual indicator
                        emoji_color = "cyan"
                        current_step_display = "Processing"
                    
                    # Include only actively processing recipes
                    active_count += 1
                    
                    # Extract wait time for display
                    wait_time = ""
                    step_info = ""
                    if "Still waiting" in message and "(" in message:
                        wait_time = message.split("(")[1].split(")")[0]
                    if "step:" in message.lower():
                        step_info = message.split("step:")[-1].strip()
                        
                    # Recipe name (extract from filename or URL)
                    # Récupérer un nom plus significatif de l'URL pour affichage
                    url_path = short_url.split("//")[-1].split("/")
                    # Ignorer le domaine et les chemins courts
                    recipe_parts = [part for part in url_path if "." not in part and len(part) > 3]
                    
                    # Si possible, prendre le dernier segment significatif (souvent le nom de la recette)
                    if recipe_parts:
                        # Prendre le segment le plus long ou le dernier
                        longest_part = max(recipe_parts, key=len) if len(recipe_parts) > 1 else recipe_parts[-1]
                        # Remplacer les tirets par des espaces et mettre en forme
                        recipe_name = longest_part.replace("-", " ").title()
                    else:
                        # Si aucun segment significatif, utiliser l'URL complète
                        recipe_name = short_url
                    
                    # Line 1: Recipe name and status with emoji indicator
                    # Calculer l'espace disponible pour la barre de progression et le pourcentage
                    progress_display = f" {progress}%"
                    
                    # D'abord construire les parties d'affichage de base
                    indicator = f"[{emoji_color}]{step_indicator}[/{emoji_color}]"
                    
                    # Nom avec format - utiliser la largeur disponible
                    name_display = f"[bold white]{recipe_name}[/bold white]"
                    
                    # Calculer l'espace total disponible
                    indicator_length = len(step_indicator) + 1  # +1 pour l'espace après
                    progress_display_length = len(progress_display)
                    
                    # Espace disponible pour le nom après réservation d'espace pour la barre de progression
                    progress_section_width = progress_width + progress_display_length + 2  # +2 pour espaces
                    
                    # Espace fixe entre le nom et la barre de progression
                    padding = 2
                    
                    # Calculer combien d'espace il reste pour aligner la barre de progression à droite
                    # Troncation simple du nom si nécessaire
                    available_name_width = display_width - indicator_length - progress_section_width - padding - 2
                    if len(recipe_name) > available_name_width:
                        recipe_name = recipe_name[:available_name_width-3] + "..."
                        name_display = f"[bold white]{recipe_name}[/bold white]"
                    
                    # Espace restant pour aligner à droite
                    remaining_space = display_width - indicator_length - len(recipe_name) - progress_section_width
                    remaining_space = max(2, remaining_space)  # Au moins 2 espaces
                    
                    # Créer la barre de progression
                    filled_width = int((progress / 100) * progress_width)
                    empty_width = progress_width - filled_width
                    progress_bar = f"[{emoji_color}]{'▮' * filled_width}[/{emoji_color}][dim]{'▯' * empty_width}[/dim]"
                    
                    # Afficher avec espacement dynamique
                    self.console.print(f" {name_display}{' ' * remaining_space}{progress_bar} [bold white]{progress_display}[/bold white]")
                    
                    # Line 2: Current step and time (indented)
                    # Information de l'étape avec code couleur plus clair
                    step_color = emoji_color
                    status_line = f" [dim]↳ Step[/dim] [{step_color}]{current_step_display}[/{step_color}]"
                    
                    if wait_time:
                        status_line += f" [dim]waiting[/dim] [yellow]{wait_time}[/yellow]"
                        if step_info:
                            status_line += f" [dim]at[/dim] [blue]{step_info}[/blue]"
                    
                    self.console.print(status_line)
                    
                    # Add a small separator between recipes
                    if i < len(in_progress_recipes) - 1:
                        self.console.print("[dim]" + "─" * display_width + "[/dim]")  # Séparateur simple avec opacité légère
                
                # If fewer recipes are displayed than the total in progress
                if active_count < stats["in_progress"]:
                    self.console.print("[dim]" + "─" * display_width + "[/dim]")  # Séparateur simple avec opacité légère
                    
                    # Au lieu d'afficher un résumé, afficher chaque recette en attente individuellement
                    remaining_count = stats["in_progress"] - active_count
                    wait_indicator = "⏳"  # Indicateur d'attente
                    emoji_color = "yellow"
                    
                    # Afficher chaque recette en attente individuellement
                    for i in range(remaining_count):
                        # Nom de la recette en attente - plus descriptif
                        recipe_name = f"Waiting recipe #{i+1}"
                        progress = 0
                        progress_display = f" {progress}%"
                        current_step_display = "Waiting for semaphore"
                        
                        # Construction similaire à celle des recettes actives
                        indicator = f"[{emoji_color}]{wait_indicator}[/{emoji_color}]"
                        
                        # Nom avec format - utiliser la largeur disponible
                        name_display = f"[bold white]{recipe_name}[/bold white]"
                        
                        # Calculer l'espace total disponible
                        indicator_length = len(wait_indicator) + 1  # +1 pour l'espace après
                        progress_display_length = len(progress_display)
                        
                        # Espace disponible pour le nom après réservation d'espace pour la barre de progression
                        progress_section_width = progress_width + progress_display_length + 2  # +2 pour espaces
                        
                        # Espace fixe entre le nom et la barre de progression
                        padding = 2
                        
                        # Calculer combien d'espace il reste pour aligner la barre de progression à droite
                        available_name_width = display_width - indicator_length - progress_section_width - padding - 2
                        if len(recipe_name) > available_name_width:
                            recipe_name = recipe_name[:available_name_width-3] + "..."
                            name_display = f"[bold white]{recipe_name}[/bold white]"
                        
                        # Espace restant pour aligner à droite
                        remaining_space = display_width - indicator_length - len(recipe_name) - progress_section_width
                        remaining_space = max(2, remaining_space)  # Au moins 2 espaces
                        
                        # Créer la barre de progression vide
                        progress_bar = f"[dim]{'▯' * progress_width}[/dim]"
                        
                        # Afficher avec espacement dynamique
                        self.console.print(f" {name_display}{' ' * remaining_space}{progress_bar} [bold white]{progress_display}[/bold white]")
                        
                        # Line 2: Current step (indented)
                        step_color = emoji_color
                        status_line = f" [dim]↳ Step[/dim] [{step_color}]{current_step_display}[/{step_color}]"
                        
                        self.console.print(status_line)
                        
                        # Ajouter un séparateur entre les recettes en attente, sauf après la dernière
                        if i < remaining_count - 1:
                            self.console.print("[dim]" + "─" * display_width + "[/dim]")  # Séparateur simple avec opacité légère
            else:
                # If no recipe is visibly in progress but the counter indicates there are
                waiting_message = "Initializing recipes..." if stats["in_progress"] > 0 else "No recipes actively processing (waiting for semaphore)"
                self.console.print(f"[yellow]{waiting_message}[/yellow]")
            
            # Final separator to close the section
            # self.console.print("[dim]" + "─" * display_width + "[/dim]")  # Séparateur simple avec opacité légère
    
    def _display_latest_error(self, now: datetime, display_width: int = 80, simple_separator: str = None, double_separator: str = None) -> None:
        """Displays the latest error if it exists."""
        # Créer les séparateurs si non fournis
        if simple_separator is None:
            simple_separator = "[dim]" + "─" * display_width + "[/dim]"
        if double_separator is None:
            double_separator = "[dim]" + "═" * display_width + "[/dim]"
            
        self.console.print(double_separator)  # Double séparateur tout en haut
        self.console.print("\n[bold cyan]Latest error[/bold cyan]")
        self.console.print(double_separator)  # Séparateur double en dessous du titre
        
        # Définition constante de la hauteur d'affichage des erreurs
        error_display_height = 13  # Augmenter de 11 à 12 lignes
        
        # Afficher la dernière erreur s'il y en a une
        if self.last_error:
            url, error_message, error_time = self.last_error
            short_url = url[:60] + "..." if len(url) > 60 else url
            elapsed_since_error = (now - error_time).total_seconds()
            
            # Ne montrer que les erreurs datant de moins de 5 minutes
            if elapsed_since_error < 300:
                # Nettoyer le message d'erreur (supprimer les timestamps et infos de process au début)
                error_lines = []
                for line in error_message.splitlines():
                    # Supprimer les timestamps et informations de process (format typique: "2023-04-13 11:10:53,787 - urllib3.connectionpool - DEBUG")
                    if " - " in line and (line.count(" - ") >= 2):
                        parts = line.split(" - ", 2)
                        if len(parts) >= 3 and parts[0].count(":") >= 2 and parts[0].count("-") >= 2:
                            # Ne garder que la partie utile du message
                            error_lines.append(parts[2])
                    else:
                        error_lines.append(line)
                
                # Calculer le nombre de lignes à afficher pour le message d'erreur
                # 1 ligne pour "Source" + 1 ligne pour le séparateur, donc error_display_height - 2
                max_error_lines = error_display_height - 2
                
                # Si le message d'erreur est trop long, n'afficher que les dernières lignes
                if len(error_lines) > max_error_lines:
                    error_display = "\n".join(error_lines[-max_error_lines:])
                else:
                    # Sinon, afficher tout le message
                    error_display = "\n".join(error_lines)
                
                # Afficher l'URL source en dim (gris) au lieu de rouge
                self.console.print(f"[dim]Source {short_url}[/dim]")
                
                # Ajouter un séparateur simple après la source
                self.console.print(simple_separator)
                
                # Afficher le message d'erreur avec retour à la ligne automatique
                wrapped_lines = []
                for line in error_display.splitlines():
                    # Découper les lignes trop longues en plusieurs lignes
                    while len(line) > 80:
                        # Trouver un espace pour couper proprement
                        split_pos = line[:80].rfind(' ')
                        if split_pos == -1:  # Pas d'espace, couper arbitrairement
                            split_pos = 80
                        
                        wrapped_lines.append(line[:split_pos])
                        line = line[split_pos:].strip()
                    
                    if line:  # Ajouter le reste de la ligne
                        wrapped_lines.append(line)
                
                # Ajuster le nombre de lignes à afficher
                max_wrapped_lines = error_display_height - 3  # -1 pour source, -1 pour séparateur, -1 pour la marge
                if len(wrapped_lines) > max_wrapped_lines:
                    wrapped_lines = wrapped_lines[-max_wrapped_lines:]
                
                # Afficher les lignes avec une couleur dim
                for line in wrapped_lines:
                    self.console.print(f"[red dim]{line}[/red dim]")
                
                # Compléter avec des lignes vides si nécessaire
                empty_lines_needed = error_display_height - 3 - len(wrapped_lines)  # -1 pour source, -1 pour séparateur, -1 pour la marge
                for _ in range(max(0, empty_lines_needed)):
                    self.console.print("")
            else:
                # Si l'erreur est trop ancienne, afficher le message par défaut centré
                self._display_centered_no_error(error_display_height)
        else:
            # Si pas d'erreur, afficher le message par défaut centré
            self._display_centered_no_error(error_display_height)
        
        self.console.print("[dim]" + "═" * display_width + "[/dim]")
    
    def _display_centered_no_error(self, height: int) -> None:
        """Affiche un message d'absence d'erreur centré dans un espace de hauteur définie."""
        # Calculer le nombre de lignes vides avant et après
        empty_lines_before = height // 2
        empty_lines_after = height - empty_lines_before - 1  # -1 pour la ligne du message
        
        # Afficher des lignes vides avant
        for _ in range(empty_lines_before):
            self.console.print("")
        
        # Afficher le message centré
        self.console.print("[dim]No recent errors[/dim]")
        
        # Afficher des lignes vides après
        for _ in range(empty_lines_after):
            self.console.print("") 