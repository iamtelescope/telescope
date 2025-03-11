# Changelog

## 2024.03.11
Version: **0.0.12**
Changes:
 - Explorer UI update: Query settings and chart settings have been moved into separate dropdown menus to improve usability and reduce interface clutter.
 - Added a placeholder for the raw query editor and made various style adjustments

## 2024.03.10 +
Version: **0.0.11**
Changes:
 - Added support for raw SQL `WHERE` statements

Related issues:
 - [ISSUE-5](https://github.com/iamtelescope/telescope/issues/5)

## 2024.03.10
Version: **0.0.10**
Changes:
 - Added support for custom fields in the "Group By" option on graphs.
 - Changed data loading behavior: now, when making a new request, the old data remains on the screen until the new data is fully loaded.
 - Bugfix for a mismatch between time values in graphs and data tables (caused by differences between UTC and non-UTC timestamps).

Related issues:
 - [ISSUE-4](https://github.com/iamtelescope/telescope/issues/4)

Notes:

{% note warning %}

This release requires database migrations to be run.

{% endnote %}

## 2024.02.27
Version: **0.0.9**

Changes:
 - Make the source severity field optional.

Related issues:
 - [ISSUE-6](https://github.com/iamtelescope/telescope/issues/6)


## 2024.02.24
Version: **0.0.8**

Changes:
 - Bugfix for non-UTC time fields in ClickHouse
 - Bugfix for specifying time with histogram range selection

## 2024.02.19
Version: **0.0.7**

Changes:
- Cosmetic login screen update.

## 2024.02.18
Version: **0.0.6**

Changes:
- Fixed monaco editor static files.

## 2024.02.17
Version: **0.0.5**

Changes:
- Fixed a bug inside fields parser.
- Updated modifiers docs.
- Added naive support for Map & Array ClickHouse types.
- Added new modifiers:
    - [href](./ui/explorer/fields.md#href), for dynamically creating HTML links.
    - [format](./ui/explorer/fields.md#format), for pretty formatting of SQL or JSON data.
    - [highlight](./ui/explorer/fields.md#highlight), for syntax highlighting of SQL or JSON data.

## 2024.02.13
Version: **0.0.4**

Changes:
- Fixed default JSON renderer to handle unserializable objects properly.

## 2024.02.13
Version: **0.0.3**

Changes:
- Added placeholders for fields and query inputs based on source fields.

## 2024.02.12
Version: **0.0.2**

Changes:
 - Initial release
