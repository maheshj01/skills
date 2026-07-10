# Templates — Clean Architecture feature

Copy-paste skeletons for a feature named **`Foo`** (`foo`). Replace the name, the
fields, and the data-source body with the real ones.

These default to the **dependency-light** path: `json_serializable` for models
and a plain immutable class for state, so they compile in any project. If the
host project uses Freezed, `get_it`, `AsyncNotifier`, etc., adapt accordingly —
see the notes under each section. Match the project; don't add dependencies a
template implies.

Contents: [1. Entity](#1-entity) · [2. Repository contract](#2-repository-contract-domain)
· [3. Use case](#3-use-case) · [4. Model](#4-model-data) · [5. Data source](#5-data-source-data)
· [6. Repository impl](#6-repository-implementation-data) · [7. State](#7-state-presentation)
· [8. Notifier + providers](#8-notifier--providers-presentation) · [9. UI](#9-ui-presentation)

---

## 1. Entity
`domain/entities/foo.dart` — pure Dart, immutable, no framework imports.

```dart
class Foo {
  const Foo({required this.id, required this.name});

  final String id;
  final String name;

  @override
  bool operator ==(Object other) =>
      other is Foo && other.id == id && other.name == name;

  @override
  int get hashCode => Object.hash(id, name);
}
```

## 2. Repository contract (domain)
`domain/repositories/foo_repository.dart` — abstract, phrased in domain terms,
returns entities. Domain never sees models or JSON.

```dart
import '../entities/foo.dart';

abstract class FooRepository {
  Future<List<Foo>> getFoos();
  Future<void> submitFoo(String id);
}
```

## 3. Use case
`domain/usecases/get_foos.dart` — one business action; callers depend on intent.

```dart
import '../entities/foo.dart';
import '../repositories/foo_repository.dart';

class GetFoos {
  const GetFoos(this._repository);
  final FooRepository _repository;

  Future<List<Foo>> call() => _repository.getFoos();
}
```

## 4. Model (data)
`data/models/foo_model.dart` — mirrors the entity and owns JSON mapping.

```dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/foo.dart';

part 'foo_model.g.dart'; // match the project's build.yaml output path

@JsonSerializable()
class FooModel {
  const FooModel({required this.id, required this.name});

  final String id;
  final String name;

  factory FooModel.fromJson(Map<String, dynamic> json) => _$FooModelFromJson(json);
  Map<String, dynamic> toJson() => _$FooModelToJson(this);

  Foo toEntity() => Foo(id: id, name: name);
}
```

> Freezed project: make `FooModel` a `@freezed` class with a `fromJson` factory
> instead. Hand-rolled project: write `fromJson`/`toJson` by hand and drop the
> `part`.

## 5. Data source (data)
`data/datasources/foo_remote_data_source.dart` — thinnest wrapper over the
client/DB. Throws on failure; no mapping to entities here.

```dart
import '../models/foo_model.dart';

abstract class FooRemoteDataSource {
  Future<List<FooModel>> fetchFoos();
  Future<void> submitFoo(String id);
}

class FooRemoteDataSourceImpl implements FooRemoteDataSource {
  const FooRemoteDataSourceImpl(this._client); // http.Client, Supabase, gRPC…
  final Object _client;

  @override
  Future<List<FooModel>> fetchFoos() async {
    // final res = await _client.get(...);
    // return (res.data as List).map(FooModel.fromJson).toList();
    throw UnimplementedError('wire the real client call');
  }

  @override
  Future<void> submitFoo(String id) async {
    throw UnimplementedError('wire the real client call');
  }
}
```

## 6. Repository implementation (data)
`data/repositories/foo_repository_impl.dart` — the only class that knows both
worlds: maps models → entities and turns exceptions into domain-friendly errors.

```dart
import '../../domain/entities/foo.dart';
import '../../domain/repositories/foo_repository.dart';
import '../datasources/foo_remote_data_source.dart';

class FooRepositoryImpl implements FooRepository {
  const FooRepositoryImpl(this._remote);
  final FooRemoteDataSource _remote;

  @override
  Future<List<Foo>> getFoos() async {
    final models = await _remote.fetchFoos();
    return models.map((m) => m.toEntity()).toList();
  }

  @override
  Future<void> submitFoo(String id) => _remote.submitFoo(id);
}
```

## 7. State (presentation)
`presentation/state/foo_state.dart` — immutable; `data + isLoading + error` plus
UI fields and computed getters so widgets stay dumb.

```dart
import '../../domain/entities/foo.dart';

class FooState {
  const FooState({
    this.foos = const [],
    this.isLoading = false,
    this.error,
    this.selected,
  });

  final List<Foo> foos;
  final bool isLoading;
  final String? error;
  final Foo? selected;

  bool get hasFoos => foos.isNotEmpty;
  bool get canSubmit => selected != null;

  FooState copyWith({
    List<Foo>? foos,
    bool? isLoading,
    String? error,      // pass null explicitly to clear via the sentinel below
    Foo? selected,
  }) =>
      FooState(
        foos: foos ?? this.foos,
        isLoading: isLoading ?? this.isLoading,
        error: error,
        selected: selected ?? this.selected,
      );
}
```

> Freezed project: replace this whole file with a `@freezed` class exposing the
> same fields/getters. `AsyncValue` project: model data as `AsyncValue<List<Foo>>`
> and skip the manual `isLoading`/`error`.

## 8. Notifier + providers (presentation)
`presentation/providers/foo_notifier.dart` — composes dependencies and runs the
standard load pattern. Never mutates state in place.

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/datasources/foo_remote_data_source.dart';
import '../../data/repositories/foo_repository_impl.dart';
import '../../domain/entities/foo.dart';
import '../../domain/repositories/foo_repository.dart';
import '../../domain/usecases/get_foos.dart';
import '../state/foo_state.dart';

final fooRemoteDataSourceProvider = Provider<FooRemoteDataSource>(
  (ref) => FooRemoteDataSourceImpl(/* ref.watch(clientProvider) */ Object()),
);

final fooRepositoryProvider = Provider<FooRepository>(
  (ref) => FooRepositoryImpl(ref.watch(fooRemoteDataSourceProvider)),
);

final getFoosProvider = Provider<GetFoos>(
  (ref) => GetFoos(ref.watch(fooRepositoryProvider)),
);

class FooNotifier extends Notifier<FooState> {
  @override
  FooState build() => const FooState();

  Future<void> loadFoos() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final foos = await ref.read(getFoosProvider)();
      state = FooState(foos: foos);
    } catch (e, st) {
      // Logger().e('loadFoos failed', e, st);  // log the real error
      state = state.copyWith(isLoading: false, error: 'Failed to load. Try again.');
    }
  }

  void select(Foo foo) {
    if (state.selected == foo) return;
    state = state.copyWith(selected: foo);
  }
}

final fooNotifierProvider =
    NotifierProvider<FooNotifier, FooState>(FooNotifier.new);
```

> `get_it` project: register the data source/repository/use case there and read
> them in the notifier instead of via providers.

## 9. UI (presentation)
`presentation/pages/foo_page.dart` — loading / error / empty / content.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/foo_notifier.dart';
import '../state/foo_state.dart';

class FooPage extends ConsumerStatefulWidget {
  const FooPage({super.key});

  @override
  ConsumerState<FooPage> createState() => _FooPageState();
}

class _FooPageState extends ConsumerState<FooPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) ref.read(fooNotifierProvider.notifier).loadFoos();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(fooNotifierProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Foo')),
      body: _body(state),
    );
  }

  Widget _body(FooState state) {
    if (state.isLoading) return const Center(child: CircularProgressIndicator());
    if (state.error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(state.error!, textAlign: TextAlign.center),
        ),
      );
    }
    if (!state.hasFoos) return const Center(child: Text('Nothing here yet.'));
    return ListView.builder(
      itemCount: state.foos.length,
      itemBuilder: (_, i) {
        final foo = state.foos[i];
        return ListTile(
          title: Text(foo.name),
          selected: state.selected == foo,
          onTap: () => ref.read(fooNotifierProvider.notifier).select(foo),
        );
      },
    );
  }
}
```

---

## Codegen

Only if models/state use `json_serializable` or Freezed. Point `part` at the
project's `build.yaml` output path, then run
`dart run build_runner build --delete-conflicting-outputs` (or `make generate`).
If nothing is generated, skip this.
