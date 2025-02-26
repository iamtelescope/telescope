# Querying data approach

## Introduction

Telescope’s approach to data querying is designed to be both **user-friendly and secure**, while remaining flexible across various sources. By leveraging [**FlyQL**](https://github.com/iamtelescope/flyql) as an abstraction layer, Telescope decouples the query language from any specific source - whether it's ClickHouse, another database, or even a file on the filesystem. This means users can work with a consistent querying interface regardless of where the data is stored, without the complexity and risks associated with raw SQL or API queries for different sources.

Currently, Telescope supports only ClickHouse as a data source. However, by utilizing FlyQL as a universal query abstraction layer, Telescope is well-positioned to extend support to other sources in the future without sacrificing a secure, controlled environment.

For most users, writing SQL queries is unnecessary overhead—it’s both time-consuming and complex. Instead, Telescope **separates field selection from query filtering**, allowing users to build queries by choosing from **explicitly allowed fields** and applying filters in a structured manner. This design enhances transparency and security in several ways:

- **Field Selector:** Ensures that users see only permitted fields, preventing the accidental exposure of sensitive data.
- **Eliminates Direct SQL Access:** Mitigates risks such as SQL injection, unauthorized network requests, or improper file system access.

Furthermore, for advanced users, future updates will introduce fine-grained permissions. This will enable specific users or groups to extend the `WHERE` clause with custom SQL conditions when necessary, adding an extra layer of flexibility without compromising system security.

By integrating FlyQL, Telescope not only simplifies the querying process but also lays the groundwork for future scalability and integration with diverse sources—all while maintaining a secure, controlled environment.

