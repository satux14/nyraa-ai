# Salon-configurable recommendations

Place `recommendations.json` here (or set `RECOMMENDATIONS_CONFIG` to your file path).

## Format

```json
{
  "rules": [
    {
      "conditions": {
        "skin_type": "Oily",
        "acne_level": ["Moderate", "High"]
      },
      "services": ["Acne Control Facial"],
      "products": ["Salicylic Cleanser"]
    }
  ]
}
```

- **conditions**: Optional. Keys: `skin_type`, `acne_level`, `face_shape`, `dark_circle_score`. Value can be a string (exact match) or list (value must be in list). All given conditions must match.
- **services** / **products**: Arrays of strings to add when the rule matches. Merged and deduplicated across all matching rules.

If the file is missing or invalid, the service falls back to built-in rules.
