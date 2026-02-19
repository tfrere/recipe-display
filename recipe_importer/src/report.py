from rich.console import Console
from rich.table import Table
from datetime import datetime
from typing import List

from .models import ImportMetrics, RecipeError


class ReportGenerator:
    """Classe responsable de la génération des rapports d'importation."""
    
    def __init__(self, console: Console = None):
        self.console = console or Console()
    
    def show_final_report(self, metrics: ImportMetrics) -> None:
        """Affiche un rapport final d'importation."""
        self.console.clear()
        
        # Calculer le temps réel écoulé depuis le début de l'importation
        elapsed_time = datetime.now() - metrics.start_time
        total_time = str(elapsed_time).split('.')[0]
        
        # Calcule le taux de réussite
        total_imported = metrics.success_count + metrics.failure_count + metrics.skip_count
        success_rate = (metrics.success_count / total_imported * 100) if total_imported > 0 else 0
        
        # En-tête
        self.console.print("\n[bold cyan]Recipe Import Results[/bold cyan]")
        self.console.print("[dim]" + "═" * 50 + "[/dim]")
        
        # Statistiques générales
        self.console.print(f"[bold]Import completed in:[/bold] [cyan]{total_time}[/cyan]")
        self.console.print(f"[bold]Total recipes processed:[/bold] [cyan]{total_imported}[/cyan]")
        
        # Créer un tableau pour plus de clarté
        table = Table(show_header=True)
        table.add_column("Status", style="bold")
        table.add_column("Count", style="cyan")
        table.add_column("Percentage", style="magenta")
        
        # Ajouter les lignes de données
        table.add_row("✅ Success", str(metrics.success_count), f"{metrics.success_count / total_imported * 100:.1f}%" if total_imported > 0 else "0%")
        table.add_row("⚠️ Skipped", str(metrics.skip_count), f"{metrics.skip_count / total_imported * 100:.1f}%" if total_imported > 0 else "0%")
        table.add_row("❌ Failed", str(metrics.failure_count), f"{metrics.failure_count / total_imported * 100:.1f}%" if total_imported > 0 else "0%")
        
        # Ajouter une ligne de total pour validation
        table.add_row("Total", str(total_imported), "100%")
        
        # Afficher le tableau
        self.console.print(table)
        
        # Afficher les erreurs
        self._show_errors(metrics.errors)
        
        # Afficher un message de conclusion
        if success_rate >= 90:
            self.console.print("\n[bold green]Import completed successfully! ✨[/bold green]")
        elif success_rate >= 70:
            self.console.print("\n[bold yellow]Import completed with some issues.[/bold yellow]")
        else:
            self.console.print("\n[bold red]Import completed with significant issues![/bold red]")
    
    def _show_errors(self, errors: List[RecipeError]) -> None:
        """Affiche les dernières erreurs d'importation."""
        if not errors:
            return
            
        self.console.print(f"\n[bold red]Errors ({len(errors)} total):[/bold red]")
        
        # Trier les erreurs par heure (plus récentes en premier)
        sorted_errors = sorted(errors, key=lambda x: x.timestamp, reverse=True)
        
        # Regrouper par type d'erreur pour un résumé utile
        error_types: dict[str, list[str]] = {}
        for error in sorted_errors:
            # Extraire le type d'erreur principal
            error_key = self._classify_error(error.error)
            if error_key not in error_types:
                error_types[error_key] = []
            error_types[error_key].append(error.url)
        
        # Afficher le résumé par type
        for error_type, urls in error_types.items():
            self.console.print(f"\n  [bold yellow]{error_type}[/bold yellow] ({len(urls)} recette{'s' if len(urls) > 1 else ''}):")
            for url in urls[:5]:
                short_url = url
                if len(short_url) > 80:
                    short_url = short_url[:40] + "..." + short_url[-35:]
                self.console.print(f"    [dim]•[/dim] {short_url}")
            if len(urls) > 5:
                self.console.print(f"    [dim]... et {len(urls) - 5} autres[/dim]")
        
        # Afficher le détail des 3 dernières erreurs
        self.console.print("\n[bold]Détails des dernières erreurs:[/bold]")
        for i, error in enumerate(sorted_errors[:3]):
            short_url = error.url
            if len(short_url) > 80:
                short_url = short_url[:40] + "..." + short_url[-35:]
            self.console.print(f"\n  {i+1}. [bold]{short_url}[/bold]")
            
            # Afficher le message complet (jusqu'à 500 chars)
            error_message = error.error
            if len(error_message) > 500:
                error_message = error_message[:500] + "..."
            self.console.print(f"     [red]{error_message}[/red]")
    
    @staticmethod
    def _classify_error(error_msg: str) -> str:
        """Classifie une erreur en catégorie lisible."""
        msg = error_msg.lower()
        if "404" in msg or "not found" in msg:
            return "404 Not Found (URL invalide)"
        elif "401" in msg or "unauthorized" in msg or "authentication" in msg:
            return "401 Unauthorized (clé API invalide)"
        elif "timeout" in msg or "timed out" in msg:
            return "Timeout (serveur LLM trop lent)"
        elif "rate limit" in msg or "429" in msg:
            return "Rate limit (trop de requêtes)"
        elif "validation" in msg or "pydantic" in msg:
            return "Erreur de validation (structure recette)"
        elif "already exists" in msg:
            return "Recette déjà existante"
        elif "bloqué" in msg or "stall" in msg:
            return "Import bloqué (pas de progression)"
        elif "connection" in msg or "connect" in msg:
            return "Erreur de connexion"
        elif "scraper" in msg and "failed" in msg:
            return "Échec du scraper"
        else:
            return "Autre erreur"