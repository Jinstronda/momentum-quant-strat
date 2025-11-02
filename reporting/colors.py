"""Dynamic color generation for reporting visualizations."""

import hashlib
import math
from typing import Dict, Optional
import pandas as pd
import matplotlib.colors as mcolors


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple:
    """Convert HSL to RGB tuple (0-1 range)."""
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    
    if 0 <= h < 60:
        r, g, b = c, x, 0
    elif 60 <= h < 120:
        r, g, b = x, c, 0
    elif 120 <= h < 180:
        r, g, b = 0, c, x
    elif 180 <= h < 240:
        r, g, b = 0, x, c
    elif 240 <= h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    
    return (r + m, g + m, b + m)


def _rgb_to_hex(rgb: tuple) -> str:
    """Convert RGB tuple (0-1 range) to hex string."""
    r, g, b = [int(min(255, max(0, x * 255))) for x in rgb]
    return f"#{r:02x}{g:02x}{b:02x}"


def _generate_distinct_color(identifier: str, index: int = 0, 
                            saturation: float = 0.7, lightness: float = 0.5) -> str:
    """
    Generate a distinct color for an identifier.
    
    Uses HSL color space with golden angle spacing for maximum distinction.
    Colors are consistent for the same identifier.
    """
    hash_val = int(hashlib.md5(str(identifier).encode()).hexdigest(), 16)
    seed = (hash_val + index * 137.508) % 1000
    
    # Use golden angle (137.508 degrees) for optimal spacing
    hue = (seed * 137.508) % 360
    
    # Adjust saturation and lightness slightly based on hash for variation
    s = saturation + (hash_val % 100) / 1000 - 0.05
    s = max(0.5, min(0.9, s))
    
    l = lightness + (hash_val % 100) / 1000 - 0.05
    l = max(0.3, min(0.7, l))
    
    rgb = _hsl_to_rgb(hue, s, l)
    return _rgb_to_hex(rgb)


def get_filter_color(filter_name: str) -> str:
    """Get distinct color for a filter name."""
    if not filter_name:
        return '#808080'
    return _generate_distinct_color(filter_name, saturation=0.75, lightness=0.55)


def get_position_color(position: Optional[str], default: str = '#808080') -> str:
    """
    Get distinct color for a position/symbol.
    
    CASH/None positions return red as error indicator.
    All other positions get dynamically generated distinct colors.
    """
    if pd.isna(position) or position is None:
        return '#FF0000'  # Red for CASH (error indicator)
    
    if isinstance(position, str) and position.upper() == 'CASH':
        return '#FF0000'  # Red for CASH
    
    return _generate_distinct_color(str(position), saturation=0.7, lightness=0.5)


def get_filter_colors(filter_names: list) -> Dict[str, str]:
    """Generate distinct colors for a list of filter names."""
    return {name: get_filter_color(name) for name in filter_names}


def get_position_colors(positions: list) -> Dict[Optional[str], str]:
    """Generate distinct colors for a list of positions."""
    return {pos: get_position_color(pos) for pos in positions}


# Legacy compatibility - maintain API but generate dynamically
def FILTER_COLORS():
    """Legacy compatibility - returns dict but generates colors dynamically."""
    default_filters = [
        'EMA(12)', 'EMA(25)', 'EMA(45)', 'EMA(63)',
        'Double_EMA(12)', 'Double_EMA(25)', 'Double_EMA(45)', 'Double_EMA(63)',
        'Double_EMA(75)', 'Double_EMA(90)', 'Double_EMA(105)', 'Double_EMA(120)',
        'TEMA(12)', 'TEMA(25)', 'TEMA(45)', 'TEMA(63)',
        'TEMA(75)', 'TEMA(90)', 'TEMA(105)', 'TEMA(120)',
    ]
    return get_filter_colors(default_filters)


def blend_colors(colors: list, weights: list) -> str:
    """
    Blend multiple hex colors by given weights.
    
    Args:
        colors: List of hex color strings (e.g., ['#FF0000', '#0000FF'])
        weights: List of weights (must sum to 1.0)
        
    Returns:
        Blended hex color string
    """
    if len(colors) != len(weights):
        raise ValueError("Colors and weights must have same length")
    
    # Convert hex to RGB
    rgb_colors = []
    for color in colors:
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        rgb_colors.append((r, g, b))
    
    # Weighted average of each channel
    r_blend = sum(rgb[0] * w for rgb, w in zip(rgb_colors, weights))
    g_blend = sum(rgb[1] * w for rgb, w in zip(rgb_colors, weights))
    b_blend = sum(rgb[2] * w for rgb, w in zip(rgb_colors, weights))
    
    # Convert back to hex
    r_blend = int(min(255, max(0, r_blend)))
    g_blend = int(min(255, max(0, g_blend)))
    b_blend = int(min(255, max(0, b_blend)))
    
    return f"#{r_blend:02x}{g_blend:02x}{b_blend:02x}"


# Maintain backward compatibility - if code expects POSITION_COLORS dict
# they can still use get_position_color() which works the same way
__all__ = ['get_filter_color', 'get_position_color', 'get_filter_colors', 
           'get_position_colors', 'FILTER_COLORS', 'blend_colors']
