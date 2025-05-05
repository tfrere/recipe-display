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
            
        self.console.print("\n[bold red]Last errors:[/bold red]")
        
        # Trier les erreurs par heure (plus récentes en premier)
        sorted_errors = sorted(errors, key=lambda x: x.timestamp, reverse=True)
        
        # Afficher les 5 dernières erreurs maximum
        for i, error in enumerate(sorted_errors[:5]):
            short_url = error.url
            # Tronquer l'URL pour l'affichage
            if len(short_url) > 70:
                short_url = short_url[:35] + "..." + short_url[-35:]
                
            # Afficher les détails de l'erreur
            self.console.print(f"{i+1}. [bold]{short_url}[/bold]")
            
            # Limiter les messages d'erreur très longs
            error_message = error.error
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
                
            self.console.print(f"   [red]{error_message}[/red]\n") 