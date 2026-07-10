---
name: flutter-clean-architecture
description: >-
  Scaffolds a new Flutter feature using Clean Architecture with Riverpod —
  domain (entities, repository contracts, use cases), data (models, data
  sources, repository implementations), and presentation (Riverpod providers,
  immutable or Freezed state, and a loading/error/empty/content UI). Use this
  skill whenever the user wants to build a new Flutter feature, screen, or flow
  — especially anything that loads data from an API or local storage into
  Riverpod state — or asks for Clean Architecture, repositories, use cases, or
  a feature-first folder structure. Always mirror the host project's existing
  stack (serialization, DI, state) rather than imposing a fixed one.
---

# Flutter Clean Architecture Feature Scaffold

Generate a production-ready Flutter feature split into three layers that depend
inward only: **presentation → domain ← data**. The point of the split is that
business rules (domain) never import Flutter, Riverpod, or any I/O package, so
they stay testable and stable while UI and data sources change freely.

Copy-paste snippets for every layer live in
[`references/templates.md`](references/templates.md) — read that file when you're
ready to write code. This file is the workflow and the decisions.

## When to use

Building a new feature/screen/flow, consuming an API, adding CRUD, wiring
authentication or local storage, creating repositories or use cases, or setting
up Riverpod providers + immutable state. If the user names "Clean Architecture,"
"repository pattern," or "feature-first," this is the skill.

## Adapt to the project first (do this before writing anything)

The generated code is worthless if it doesn't compile in *this* repo, so match
what already exists instead of assuming a canonical stack. Before scaffolding,
scan the project and settle four things:

- **Serialization** — Freezed? `json_serializable`? hand-written `toJson`? Use
  whatever the project already depends on. Do **not** add Freezed to a project
  that doesn't use it just to follow a template.
- **State** — Freezed unions, a plain immutable class with `copyWith`, or
  `AsyncValue`/`AsyncNotifier`. Follow the prevailing style.
- **DI** — Riverpod providers, `get_it`, or manual construction. Compose
  dependencies the way the rest of the app does.
- **Folder layout** — if the project is already feature-first (or layer-first),
  match it. Only introduce the structure below when there's no convention yet.

Check `pubspec.yaml` and an existing feature to infer these. When you pick a
default because the project is silent, say so in one line.

## Architecture

```
presentation/  pages · widgets · providers · state   (Flutter + Riverpod)
domain/        entities · repository contracts · use cases   (pure Dart)
data/          models · data sources · repository impls   (I/O, mapping)
```

Dependency flow — each arrow is "depends on", and it only points inward:

```
UI → Notifier/Controller → UseCase → Repository (contract) ← RepositoryImpl → DataSource
```

The UI never touches a repository, data source, or client directly; it watches
state and calls the notifier. Networking/persistence lives behind the
repository. The domain layer defines the repository *interface*; the data layer
implements it — that inversion is what keeps domain free of I/O.

## Folder structure (feature-first, when no convention exists)

```
lib/features/<feature>/
├── data/         datasources/  models/  repositories/   (impls)
├── domain/       entities/     repositories/ (contracts)  usecases/
└── presentation/ pages/  widgets/  providers/  state/
```

## Naming (feature "User")

| Layer | Symbols |
|-------|---------|
| domain | `UserEntity`, `UserRepository` (abstract), `GetUsers` (use case) |
| data | `UserModel`, `UserRemoteDataSource`, `UserRepositoryImpl` |
| presentation | `UserState`, `UserNotifier`, `UserPage` |
| providers | `userRemoteDataSourceProvider`, `userRepositoryProvider`, `getUsersProvider`, `userNotifierProvider` |

Keep singular/plural consistent (`UserEntity`, `getUsers`).

## Build order

Work outside-in on contracts, then fill implementations — it keeps each step
compiling against a known interface.

```
- [ ] 0. Clarify + detect project stack (serialization, state, DI, layout)
- [ ] 1. Entity        (domain/entities)        pure Dart, no framework imports
- [ ] 2. Repository contract (domain/repositories)  abstract methods over entities
- [ ] 3. Use case(s)   (domain/usecases)         one action each, call the contract
- [ ] 4. Model         (data/models)             maps to/from Entity + JSON
- [ ] 5. Data source   (data/datasources)        raw I/O, throws on failure
- [ ] 6. Repository impl (data/repositories)      maps Model→Entity, handles errors
- [ ] 7. State         (presentation/state)       immutable: data + loading + error
- [ ] 8. Notifier + providers (presentation/providers)
- [ ] 9. UI            (presentation/pages)        loading/error/empty/content
- [ ] 10. Codegen if needed, then explain how to wire routing (don't wire unasked)
```

## Layer guidance

**Domain** is the core and imports nothing but Dart. Entities are plain
immutable value objects. Repository contracts are abstract classes phrased in
domain terms. A use case wraps a single business action (`GetUsers`,
`SubmitOrder`) so callers depend on intent, not on repository breadth — and so
logic is unit-testable without Flutter.

**Data** does I/O and translation. A model extends/mirrors an entity and owns
JSON (or protobuf) mapping. A data source is the thinnest wrapper over the
client/DB and throws on failure. The repository implementation maps models to
entities and turns exceptions into domain-friendly failures (or rethrows) — it's
the only place that knows both worlds.

**Presentation** observes and triggers. State is immutable and typically carries
`isLoading`, `error`, and the data, plus UI fields (selection, query, step,
CTA-loading) and computed getters (`canSubmit`) so widgets stay dumb. The
notifier orchestrates use cases and rewrites state; it never mutates in place.
Widgets watch state and call notifier methods — nothing more.

## The standard load pattern

Every fetch follows the same shape so behaviour is predictable:

1. Set `isLoading: true`, clear `error` (and stale data/selection).
2. `await` the use case.
3. On success → data + `isLoading: false`.
4. On failure → `isLoading: false` + a user-facing `error` string (never a raw
   exception). Log the real error.

Mutations mirror this with a CTA-loading flag and advance a step / clear error on
success.

## UI

Generate a lightweight `ConsumerWidget`/`ConsumerStatefulWidget` that kicks off
the load in `initState` via `addPostFrameCallback`, then branches on state:
**loading** → spinner, **error** → centered message, **empty** → empty message,
**content** → the list/detail. Disable the primary CTA until state says it's
ready. Use Material defaults unless the project has a design system — then use
that. Don't over-style.

## Codegen

Only if the chosen serialization/state uses it. Match the project's `build.yaml`
output path for `part` directives, then run `dart run build_runner build
--delete-conflicting-outputs` (or the project's `make generate`). If nothing is
generated, skip this entirely.

## Success criteria

- Domain has zero Flutter/Riverpod/HTTP imports.
- The repository interface is in domain; its implementation is in data.
- State is immutable with `copyWith`; the notifier never mutates fields in place.
- UI never calls a data source, repository, or client directly.
- Serialization, state, and DI match the host project — no stray dependencies.
- The feature compiles on its own (the page may be unrouted until wired).
