---
name: flutter-searchfield
description: Implement and customize the SearchField widget for Flutter autocomplete functionality. Use when implementing search/autocomplete features, dropdown searches, or when the user mentions SearchField, autocomplete, or suggestion lists in Flutter.
---

# Flutter SearchField Implementation

SearchField is a highly customizable autocomplete widget for Flutter.

## Installation

```bash
flutter pub add searchfield
```

Or add manually to `pubspec.yaml`:

```yaml
dependencies:
  searchfield: ^2.0.0
```

```dart
import 'package:searchfield/searchfield.dart';
```

## Quick Start

Implementation follows three core steps: initialize suggestions, map to SearchFieldListItem, and add the widget.

### Step 1: Initialize Suggestions

```dart
late List<SearchFieldListItem<YourType>> items;
YourType? selectedValue;

@override
void initState() {
  items = yourDataList.map((item) {
    return SearchFieldListItem<YourType>(
      item.searchableProperty,  // Required: search performed on this
      value: item.displayValue, // Optional: shown in input on selection
      item: item,              // Optional: custom object
      child: customWidget,     // Optional: custom suggestion widget
    );
  }).toList();
  super.initState();
}
```

### Step 2: Add SearchField Widget

```dart
SearchField<YourType>(
  hint: 'Search placeholder',
  suggestions: items,
  selectedValue: selectedValue,
  onSuggestionTap: (SearchFieldListItem<YourType> item) {
    setState(() {
      selectedValue = item;
    });
  },
  onSearchTextChanged: (query) {
    // Return filtered list based on query
    if (query.isEmpty) return items;
    return items.where((item) =>
      item.searchKey.toLowerCase().contains(query.toLowerCase())
    ).toList();
  },
)
```

## Common Patterns

### Pattern 1: Basic Text Search

For simple string lists without custom objects:

```dart
SearchField(
  suggestions: ['Item 1', 'Item 2', 'Item 3']
    .map((e) => SearchFieldListItem<String>(e))
    .toList(),
  suggestionState: Suggestion.expand,
  onSuggestionTap: (item) {
    // Handle selection
  },
)
```

### Pattern 2: Complex Objects with Custom Display

When displaying rich content in suggestions:

```dart
SearchFieldListItem<City>(
  city.name,                    // Search key
  value: city.zipCode,          // Value shown in input on select
  item: city,                   // Full object for reference
  child: Row(                   // Custom widget
    children: [
      Icon(Icons.location_city),
      SizedBox(width: 8),
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(city.name, style: TextStyle(fontWeight: FontWeight.bold)),
          Text(city.zipCode, style: TextStyle(fontSize: 12)),
        ],
      ),
    ],
  ),
)
```

### Pattern 3: Network Loading with Pagination

Load suggestions dynamically from API:

```dart
SearchField(
  onTap: () async {
    // Trigger initial load
    final results = await fetchFromAPI();
    setState(() => suggestions = results);
  },
  onSearchTextChanged: (query) {
    // Filter or fetch based on query
    return filteredSuggestions
      .map((e) => SearchFieldListItem<String>(e))
      .toList();
  },
  emptyWidget: Container(
    height: 100,
    child: Center(
      child: CircularProgressIndicator(),
    ),
  ),
  onScroll: (position, maxScroll) {
    // Load more when near bottom
    if (position > maxScroll * 0.8) {
      loadMoreItems();
    }
  },
)
```

## Customization Guide

### Input Field Styling

Use `searchInputDecoration` for TextField-like customization:

```dart
searchInputDecoration: SearchInputDecoration(
  prefixIcon: Icon(Icons.search),
  suffixIcon: Icon(Icons.arrow_drop_down),
  hintStyle: TextStyle(color: Colors.grey),
  border: OutlineInputBorder(
    borderRadius: BorderRadius.circular(8),
  ),
  focusedBorder: OutlineInputBorder(
    borderSide: BorderSide(color: Colors.blue, width: 2),
  ),
  filled: true,
  fillColor: Colors.grey[100],
)
```

### Suggestion List Styling

Customize the dropdown container:

```dart
suggestionsDecoration: SuggestionDecoration(
  border: Border.all(color: Colors.grey),
  borderRadius: BorderRadius.circular(8),
  color: Colors.white,
  hoverColor: Colors.grey.shade200,
)
```

### Individual Suggestion Item Styling

Style each suggestion item:

```dart
suggestionItemDecoration: SuggestionDecoration(
  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
  color: Colors.grey.shade200,
  borderRadius: BorderRadius.all(Radius.circular(2)),
)
```

## Advanced Features

### Form Validation

Integrate with Flutter Forms:

```dart
Form(
  key: _formKey,
  child: SearchField(
    suggestions: validOptions.map((e) => SearchFieldListItem(e)).toList(),
    validator: (value) {
      if (value == null || value.isEmpty) {
        return 'Please select an option';
      }
      if (!validOptions.contains(value)) {
        return 'Please select a valid option';
      }
      return null;
    },
    autovalidateMode: AutovalidateMode.onUserInteraction,
  ),
)
```

### Keyboard Navigation

Enabled by default for desktop platforms:

- `↑/↓` - Navigate suggestions (circular)
- `Ctrl/Option + ↓` - Jump to last item
- `Ctrl/Option + ↑` - Jump to first item
- `Enter` - Select highlighted suggestion
- `Esc` - Close suggestions

### Dynamic Height Suggestions

Allow variable height items:

```dart
SearchField(
  dynamicHeight: true,
  maxSuggestionBoxHeight: 400,  // Maximum viewport height
  suggestions: items.map((item) =>
    SearchFieldListItem(
      item.name,
      child: Container(
        // Variable height content
        child: Column(
          children: [
            Text(item.title),
            if (item.hasSubtitle) Text(item.subtitle),
          ],
        ),
      ),
    ),
  ).toList(),
)
```

### Positioning Control

Control suggestion list position:

```dart
SearchField(
  suggestionDirection: SuggestionDirection.up,  // Show above input
  offset: Offset(0, 10),  // Offset from input field
  // Direction auto-adjusts based on available space
)
```

## Key Properties Reference

**Essential Properties:**

- `suggestions` (required) - List of SearchFieldListItem
- `onSuggestionTap` - Callback when suggestion selected
- `onSearchTextChanged` - Filter logic, returns filtered suggestions
- `selectedValue` - Currently selected item
- `hint` - Placeholder text

**Display Configuration:**

- `itemHeight` - Fixed height per item (default: 51.0)
- `dynamicHeight` - Enable variable item heights
- `maxSuggestionsInViewPort` - Max visible items
- `maxSuggestionBoxHeight` - Max dropdown height (with dynamicHeight)

**Behavior:**

- `suggestionState` - Controls initial suggestion visibility:
  - `Suggestion.expand` — Show suggestions immediately when the field is focused (common for dropdown-style pickers)
  - `Suggestion.hidden` — Show suggestions only after the user starts typing (common for search-style inputs)
- `autoCorrect` - Enable autocorrect (default: true)
- `enabled` - Enable/disable widget (default: true)
- `readOnly` - Make input read-only (default: false)
- `keepSearchOnSelection` - Keep search text in the field after selecting a suggestion (default: false)
- `textInputAction` - Keyboard action button
- `textCapitalization` - Configures keyboard uppercase/lowercase behavior
- `textAlign` - Alignment of the text in the searchfield (default: TextAlign.start)
- `inputFormatters` - Input formatters for the search field
- `SuggestionAction` - Enum to control focus behavior on suggestion tap

**Callbacks:**

- `onTap` - When field gains focus
- `onSubmit` - When form submitted
- `onOutsideTap` - When tapping outside
- `onScroll` - Scroll position updates (for pagination)
- `showEmpty` - Boolean to show/hide the emptyWidget

**Styling:**

- `searchInputDecoration` - Input field decoration
- `suggestionsDecoration` - Dropdown container decoration
- `suggestionItemDecoration` - Individual item decoration
- `searchStyle` - Text style for input
- `suggestionStyle` - Text style for suggestions
- `scrollbarDecoration` - Decoration for the scrollbar
- `marginColor` - Color for the margin between suggestions

**Controllers:**

- `controller` - TextEditingController
- `focusNode` - FocusNode for focus management
- `scrollController` - Control suggestion list scroll

## Common Issues

### Issue: Suggestions not filtering

**Cause**: `onSearchTextChanged` not returning filtered list

**Solution**: Always return a filtered List<SearchFieldListItem> from `onSearchTextChanged`:

```dart
onSearchTextChanged: (query) {
  if (query.isEmpty) return allSuggestions;

  return allSuggestions.where((item) {
    return item.searchKey.toLowerCase().contains(query.toLowerCase());
  }).toList();
}
```

### Issue: Selected value not displaying

**Cause**: Not updating `selectedValue` in setState

**Solution**: Update state in onSuggestionTap:

```dart
onSuggestionTap: (item) {
  setState(() {
    selectedValue = item;
  });
}
```

### Issue: Form validation not working

**Cause**: SearchField not wrapped in Form or missing validator

**Solution**: Ensure Form wrapper and provide validator:

```dart
Form(
  key: _formKey,
  child: SearchField(
    validator: (value) {
      if (value == null || value.isEmpty) {
        return 'Required field';
      }
      return null;
    },
  ),
)
```

## Example Code References

For complete examples, see:

- [Basic implementation](https://github.com/maheshj01/searchfield/blob/master/example/lib/main.dart)
- [Network loading](https://github.com/maheshj01/searchfield/blob/master/example/lib/network_sample.dart)
- [Custom widgets](https://github.com/maheshj01/searchfield/blob/master/example/lib/custom.dart)
- [Pagination](https://github.com/maheshj01/searchfield/blob/master/example/lib/pagination.dart)
