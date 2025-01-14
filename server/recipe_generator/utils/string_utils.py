import re

def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    # Convert to lowercase
    slug = title.lower()
    
    # Replace accented characters
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e',
        'à': 'a', 'â': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'û': 'u', 'ü': 'u',
        'ç': 'c'
    }
    for old, new in replacements.items():
        slug = slug.replace(old, new)
    
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Remove hyphens at the beginning and end
    return slug.strip('-')

def parse_time_to_minutes(time_str: str) -> float:
    """Convert a time string (e.g. '1h30min' or '45min') to minutes."""
    if time_str == "N/A":
        return 0
    
    total_minutes = 0
    
    # Si c'est un intervalle (e.g., "5-6min"), prendre la valeur minimale
    if '–' in time_str or '-' in time_str:
        parts = re.split(r'[–-]', time_str)
        time_str = parts[0].strip()  # Prendre la valeur minimale
    
    if 'h' in time_str:
        hours = float(time_str.split('h')[0])
        minutes_part = time_str.split('h')[1].strip()
        total_minutes = hours * 60
        
        if 'min' in minutes_part:
            minutes = float(minutes_part.split('min')[0])
            total_minutes += minutes
    elif 'min' in time_str:
        minutes = float(time_str.split('min')[0])
        total_minutes = minutes
        
    return total_minutes