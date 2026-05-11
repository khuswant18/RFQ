"""Steel formulas and constants."""
from typing import Dict, Any

# BIS standard formulas for steel weight calculation
WEIGHT_FORMULAS = {
    "TMT_Bar": {
        "formula": "D² / 162.28 (kg/m)",
        "description": "BIS standard for round bars",
        "density_g_cm3": 7.85
    },
    "Structural_Plate": {
        "formula": "L × W × T × 7.85 / 1000000 (kg)",
        "description": "Volume × density for plates",
        "density_g_cm3": 7.85
    },
    "Angle": {
        "formula": "(A + B - T) × T × 0.00785 (kg/m)",
        "description": "Standard angle weight formula",
        "density_g_cm3": 7.85
    },
    "Channel": {
        "formula": "Varies by section size", 
        "description": "IS Handbook Table 1",
        "density_g_cm3": 7.85
    },
    "Flat_Bar": {
        "formula": "W × T × 7.85 / 1000 (kg/m)",
        "description": "Width × Thickness × density",
        "density_g_cm3": 7.85
    }
}

# Standard lengths
STANDARD_LENGTHS = {
    "TMT_Bar": [20, 40],  # feet
    "Structural_Plate": [6000, 12000],  # mm
    "Angle": [6000, 12000],  # mm
    "Channel": [6000, 12000],  # mm
    "Flat_Bar": [6000, 12000]  # mm
}

# Grade to IS Code mapping
GRADE_IS_CODE_MAP = {
    "Fe 415": "IS 1786:2008",
    "Fe 500": "IS 1786:2008",
    "Fe 500D": "IS 1786:2008",
    "Fe 550": "IS 1786:2008",
    "Fe 600": "IS 1786:2008",
    "E250": "IS 2062:2011",
    "E350": "IS 2062:2011",
    "E410": "IS 2062:2011"
}

# Material to IS Code mapping
MATERIAL_IS_CODE_MAP = {
    "TMT_Bar": "IS 1786:2008",
    "Structural_Plate": "IS 2062:2011",
    "Angle": "IS 2062:2011",
    "Channel": "IS 2062:2011",
    "Flat_Bar": "IS 2062:2011",
    "Square_Bar": "IS 2062:2011",
    "Pipe": "IS 1239:2004"
}
