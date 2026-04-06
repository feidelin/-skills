# JSON Config Schema Reference

## Top-Level Structure

```json
{
  "sheets": [ ... ],          // Array of sheet configs (multi-sheet mode)
  "print_settings": { ... }   // Optional global print settings
}
```

If `sheets` is omitted, the top-level object is treated as a single sheet config.

## Sheet Config

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Sheet name (default: "Sheet1") |
| `headers` | array | Yes | Column headers (strings or `{text, style}` objects) |
| `data` | array[array] | Yes | 2D array of row data |
| `column_types` | array[string] | No | Type per column: `"number"`, `"float"`, `"percent"`, `"currency_usd"`, `"currency_cny"`, `"date"`, `"bool"`, `"text"` |
| `column_widths` | array[number] | No | Width per column (null = auto) |
| `auto_width` | bool | No | Auto-calculate column widths (default: true) |
| `header_style` | StyleObject | No | Style for all headers (default: blue bg, white bold text) |
| `data_style` | StyleObject | No | Style for all data cells (default: alternating rows) |
| `merge_cells` | array | No | Merge ranges: strings `"A1:C1"` or `{start_row, start_col, end_row, end_col, value?, style?}` |
| `freeze_pane` | string | No | Freeze pane position, e.g. `"A2"` (freeze header row) |
| `auto_filter` | bool | No | Enable auto-filter on header row |
| `row_heights` | object | No | `{"1": 30, "2": 20}` — row number to height mapping |
| `title_row` | object | No | `{text, style?, height?}` — title row spanning all columns |
| `charts` | array | No | Chart configs (see Charts section) |
| `data_validations` | array | No | Data validation configs (see Validation section) |
| `conditional_formats` | array | No | Conditional formatting configs (see CF section) |

## StyleObject

```json
{
  "font": {
    "name": "Calibri",
    "size": 11,
    "bold": false,
    "italic": false,
    "color": "000000",
    "underline": false,
    "strikethrough": false
  },
  "fill": {
    "color": "4472C4",
    "type": "solid"
  },
  "alignment": {
    "horizontal": "center",   // "left", "center", "right", "general"
    "vertical": "center",     // "top", "center", "bottom"
    "wrap_text": true,
    "text_rotation": 0,
    "indent": 0
  },
  "border": {
    "all": {"style": "thin", "color": "000000"}
    // Or individually: "left", "right", "top", "bottom"
    // Styles: "thin", "medium", "thick", "dashed", "dotted", "double"
  },
  "number_format": "0.00%"   // Predefined key or custom Excel format string
}
```

## Charts

```json
{
  "type": "bar",           // "bar", "line", "pie", "area", "scatter"
  "title": "Sales Chart",
  "x_column": 1,           // Column index (1-based) for X axis categories
  "y_columns": [2, 3],     // Column indices for data series
  "x_title": "Month",
  "y_title": "Revenue",
  "position": "E2",        // Cell where chart top-left is placed
  "width": 15,
  "height": 10
}
```

## Data Validations

```json
{
  "type": "list",                      // "list", "whole", "decimal", "date", "textLength"
  "formula": "Option1,Option2,Option3", // For list type: comma-separated values
  "range": "B2:B100",
  "min": 0, "max": 100,               // For whole/decimal/textLength
  "prompt_title": "Select",
  "prompt_message": "Choose a value",
  "error_title": "Error",
  "error_message": "Invalid value"
}
```

## Conditional Formatting

```json
{
  "type": "cell_is",           // "cell_is", "color_scale", "data_bar"
  "range": "C2:C100",
  "operator": "greaterThan",   // For cell_is: greaterThan, lessThan, equal, between, etc.
  "formula": "90",
  "font_color": "006100",
  "fill_color": "C6EFCE",
  // For color_scale:
  "start_color": "F8696B",
  "mid_color": "FFEB84",
  "end_color": "63BE7B",
  // For data_bar:
  "color": "638EC6"
}
```

## Print Settings

```json
{
  "orientation": "landscape",   // "portrait" or "landscape"
  "paper_size": 9,              // 1=Letter, 9=A4
  "fit_to_page": true,
  "fit_to_width": 1,
  "fit_to_height": 0
}
```
